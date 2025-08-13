from __future__ import annotations

from typing import List, Tuple
import re
import numpy as np
import pandas as pd

from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef
from django.utils import timezone

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from core.models import Clinical_note, NotePrediction

# -------------------------
# Keyword fallback (if not enough labels)
# -------------------------
KEYWORDS = {
    "ENDO": [
        r"\binsulin\b", r"\bglucose\b", r"\ba1c\b", r"\bmetformin\b",
        r"\bhyperglyc?emia\b", r"\bhypoglyc?emia\b", r"\bthyroid\b",
    ],
    "CARD": [
        r"\bchest pain\b", r"\bmi\b", r"\bmyocard(ial|ium)\b", r"\bekg\b",
        r"\bstent\b", r"\bangiogram\b", r"\bcardio\b", r"\bstatin\b",
    ],
    "PCP": [
        r"\bprimary care\b", r"\bannual (exam|visit|physical)\b",
        r"\bfollow[- ]?up\b", r"\bblood pressure\b", r"\brefill\b",
    ],
}

def keyword_route(text: str) -> Tuple[str, float]:
    """Return (specialty, confidence[0..1]) via transparent keyword rules."""
    t = text.lower()
    scores = []
    for spec, patterns in KEYWORDS.items():
        hits = sum(1 for p in patterns if re.search(p, t))
        scores.append((spec, hits))
    # pick best, break ties deterministically
    best_spec, best_hits = max(scores, key=lambda x: (x[1], x[0]))
    if best_hits == 0:
        return "OTHER", 0.50  # low confidence default
    total_hits = sum(h for _, h in scores) or 1
    conf = min(0.95, 0.60 + 0.35 * (best_hits / total_hits))
    return best_spec, float(conf)

# -------------------------
# Helpers
# -------------------------

def text_for(note: Clinical_note) -> str:
    # Build a single text field (Transcription primary; add Description/Keywords if present)
    parts = [note.Transcription or ""]
    if getattr(note, "Description", ""):
        parts.append(note.Description)
    if getattr(note, "Keywords", ""):
        parts.append(note.Keywords)
    return "\n".join(parts).strip()

def labeled_qs():
    return Clinical_note.objects.exclude(Medical_specialty__isnull=True).exclude(Medical_specialty="").only(
        "id","Medical_specialty","Transcription","Description","Keywords"
    )

def unlabeled_or_unpredicted_qs():
    # notes without any prediction yet
    sub = NotePrediction.objects.filter(Note_id=OuterRef("pk"))
    return Clinical_note.objects.annotate(has_pred=Exists(sub)).filter(has_pred=False).only(
        "id","Transcription","Description","Keywords"
    )

# -------------------------
# Command
# -------------------------

class Command(BaseCommand):
    help = "Train a text classifier (if labeled notes exist) and score new notes into NotePrediction."

    def add_arguments(self, parser):
        parser.add_argument("--min-labels", type=int, default=50, help="Need at least this many labeled notes to train.")
        parser.add_argument("--dry-run", action="store_true", help="Show what would happen without writing predictions.")
        parser.add_argument("--max", type=int, default=None, help="Limit number of new notes to predict (debug).")

    def handle(self, *args, **opts):
        min_labels = opts["min_labels"]
        dry = opts["dry_run"]
        limit = opts["max"]

        # 1) Build training set if available
        L = list(labeled_qs().values("id", "Medical_specialty", "Transcription", "Description", "Keywords"))
        y_labels = [row["Medical_specialty"].strip().upper() for row in L]
        X_texts = [text_for(Clinical_note(id=row["id"], Transcription=row["Transcription"],
                                          Description=row["Description"], Keywords=row["Keywords"])) for row in L]
        # Drop empties / normalize
        train_pairs = [(t, y) for t, y in zip(X_texts, y_labels) if t and y]
        X_texts = [t for t, _ in train_pairs]
        y_labels = [y for _, y in train_pairs]

        use_supervised = len(train_pairs) >= min_labels and len(set(y_labels)) >= 2

        if use_supervised:
            # 2) Train simple TF-IDF + LogisticRegression (multiclass) on ALL labeled notes
            vect = TfidfVectorizer(lowercase=True, stop_words="english",
                                   ngram_range=(1,2), min_df=2, max_df=0.95)
            X = vect.fit_transform(X_texts)
            clf = LogisticRegression(max_iter=1000, n_jobs=None, multi_class="auto")
            clf.fit(X, y_labels)

        # 3) Select notes to score (those with no prediction)
        P = unlabeled_or_unpredicted_qs()
        if limit:
            P = P.order_by("id")[:limit]
        P = list(P)
        if not P:
            self.stdout.write(self.style.WARNING("No new notes to score."))
            return

        now = timezone.now()
        to_create = []

        if use_supervised:
            self.stdout.write(self.style.SUCCESS(f"Training set: {len(train_pairs)} notes, classes={sorted(set(y_labels))}"))
            texts = [text_for(n) for n in P]
            Xp = vect.transform(texts)
            # Probabilities for confidence
            try:
                probs = clf.predict_proba(Xp)
                preds = clf.classes_[np.argmax(probs, axis=1)]
                confs = probs.max(axis=1)
            except Exception:
                # Fallback if probas not available
                decision = clf.decision_function(Xp)
                if decision.ndim == 1:
                    # Binary-like decision → pseudo-proba
                    confs = 1.0 / (1.0 + np.exp(-np.abs(decision)))
                    preds = np.where(decision >= 0, clf.classes_[1], clf.classes_[0])
                else:
                    # Multiclass decision → softmax
                    e = np.exp(decision - decision.max(axis=1, keepdims=True))
                    probs = e / e.sum(axis=1, keepdims=True)
                    preds = clf.classes_[np.argmax(probs, axis=1)]
                    confs = probs.max(axis=1)

            for note, spec, c in zip(P, preds, confs):
                to_create.append(NotePrediction(
                    Note=note,
                    Predicted_specialty=str(spec).upper(),
                    Confidence=float(c),
                    Predicted_at=now,
                ))
        else:
            self.stdout.write(self.style.WARNING(
                f"Not enough labeled notes to train (found {len(train_pairs)}). Using keyword routing."
            ))
            for note in P:
                spec, conf = keyword_route(text_for(note))
                to_create.append(NotePrediction(
                    Note=note,
                    Predicted_specialty=spec,
                    Confidence=conf,
                    Predicted_at=now,
                ))

        if opts["dry_run"]:
            self.stdout.write(self.style.HTTP_INFO(f"[DRY RUN] Would create {len(to_create)} NotePrediction rows."))
            return

        NotePrediction.objects.bulk_create(to_create, batch_size=1000)
        by_spec = {}
        for npred in to_create:
            by_spec[npred.Predicted_specialty] = by_spec.get(npred.Predicted_specialty, 0) + 1

        self.stdout.write(self.style.SUCCESS(
            f"Wrote {len(to_create)} NotePrediction rows at {now:%Y-%m-%d %H:%M}. "
            f"Mix: " + ", ".join(f"{k}:{v}" for k,v in sorted(by_spec.items()))
        ))
