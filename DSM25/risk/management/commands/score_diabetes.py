from __future__ import annotations

import numpy as np
import pandas as pd

from django.core.management.base import BaseCommand
from django.db.models import Max
from django.utils import timezone

from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest

from core.models import Patient_lab, RiskScore

ACTIVITY_MAP = {"low": 0, "moderate": 1, "medium": 1, "high": 2, "none": 0, "": 0, None: 0}

FEATURES = [
    "Age", "BMI", "Systolic_BP", "Diastolic_BP",
    "Total_Cholesterol", "HDL_Cholesterol", "LDL_Cholesterol",
    "Triglycerides", "Smoking_status", "Physical_Activity_Level",
]

def labs_queryset():
    # latest Patient_lab per patient
    latest_ids = (
        Patient_lab.objects
        .values("Patient_id")
        .annotate(max_id=Max("id"))
        .values_list("max_id", flat=True)
    )
    return (
        Patient_lab.objects
        .filter(id__in=list(latest_ids))
        .select_related("Patient_id")
        .order_by("Patient_id_id")
    )

def row_to_dict(lab: Patient_lab) -> dict:
    return {
        "Patient_id": lab.Patient_id_id,
        "Age": lab.Age or 0,
        "BMI": float(lab.BMI or 26.0),
        "Systolic_BP": float(lab.Systolic_BP or 125.0),
        "Diastolic_BP": float(lab.Diastolic_BP or 78.0),
        "Total_Cholesterol": float(lab.Total_Cholesterol or 190.0),
        "HDL_Cholesterol": float(lab.HDL_Cholesterol or 50.0),
        "LDL_Cholesterol": float(lab.LDL_Cholesterol or 110.0),
        "Triglycerides": float(lab.Triglycerides or 120.0),
        "Smoking_status": 1 if bool(lab.Smoking_status) else 0,
        "Physical_Activity_Level": ACTIVITY_MAP.get(
            (lab.Physical_activity or "").strip().lower(), 0
        ),
    }

class Command(BaseCommand):
    help = "Train a simple IsolationForest on DB features and write RiskScore outcomes."

    def add_arguments(self, parser):
        parser.add_argument("--fraction", type=float, default=0.05,
                            help="Top fraction to mark as HighRisk (default 0.05 = 5%)")
        parser.add_argument("--dry-run", action="store_true", help="Compute but do not write to DB")

    def handle(self, *args, **opts):
        frac = opts["fraction"]
        dry = opts["dry_run"]

        qs = labs_queryset()
        labs = list(qs)
        if not labs:
            self.stdout.write(self.style.WARNING("No Patient_lab rows found. Nothing to score."))
            return

        # Build DataFrame
        rows = [row_to_dict(l) for l in labs]
        df = pd.DataFrame(rows)

        # Matrix
        X = df[FEATURES].values.astype(float)

        # Scale + IsolationForest
        scaler = StandardScaler()
        Xs = scaler.fit_transform(X)

        model = IsolationForest(contamination=frac, random_state=42)
        model.fit(Xs)

        # Scores: IsolationForest decision_function → higher = less anomalous.
        # We invert and min-max normalize to 0..1 so higher = higher risk.
        raw = model.decision_function(Xs)
        inv = -raw
        inv -= inv.min()
        if inv.max() > 0:
            inv /= inv.max()
        scores = inv

        # Top fraction as HighRisk
        n = len(scores)
        k = max(1, int(round(frac * n)))
        cutoff = np.partition(scores, -k)[-k]  # k-th largest
        high_flags = scores >= cutoff

        now = timezone.now()
        if dry:
            self.stdout.write(self.style.HTTP_INFO(
                f"[DRY RUN] Would score {n} patients. "
                f"HighRisk fraction={frac:.2%} (cutoff={cutoff:.3f}). "
                f"Sample: score={scores[0]:.3f}, high={bool(high_flags[0])}"
            ))
            return

        # Write outcomes
        to_create = [
            RiskScore(
                Patient_id_id=int(pid),
                Score=float(s),
                HighRisk=bool(h),
                Scored_at=now
            )
            for pid, s, h in zip(df["Patient_id"].values, scores, high_flags)
        ]
        RiskScore.objects.bulk_create(to_create, batch_size=1000)

        low = float(np.mean(~high_flags))
        high = float(np.mean(high_flags))
        self.stdout.write(self.style.SUCCESS(
            f"Wrote {len(to_create)} RiskScore rows @ {now.isoformat()}. "
            f"HighRisk {high:.1%} • NotHigh {low:.1%} (cutoff={cutoff:.3f})"
        ))
