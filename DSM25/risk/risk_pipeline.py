
from __future__ import annotations

from typing import List, Tuple, Optional
import numpy as np

from django.utils import timezone
from django.db import transaction

from core.models import Customer, Patient_lab, Risk_Score

# Optional labels; if not present, we auto-fallback to rule-based
try:
    from core.models import DiabetesOutcome
    HAVE_LABELS = True
except Exception:
    DiabetesOutcome = None
    HAVE_LABELS = False

# -----------------------
# Feature engineering
# -----------------------

ACTIVITY_MAP = {
    "none": 0, "no": 0, "sedentary": 0,
    "low": 1, "light": 1,
    "moderate": 2, "medium": 2,
    "high": 3, "vigorous": 3,
}

FEATURE_NAMES = [
    "Age", "BMI", "Systolic_BP", "Diastolic_BP",
    "Total_Cholesterol", "HDL_Cholesterol", "LDL_Cholesterol", "Triglycerides",
    "Smoking_status", "Physical_activity_num",
    "Pulse_Pressure", "Chol_HDL_Ratio", "Non_HDL",
    "BP_Stage", "BMI_Cat",
]

def _norm_activity(raw: str | None) -> int:
    if not raw:
        return 1  # default low
    return ACTIVITY_MAP.get(str(raw).strip().lower(), 1)

def _bmi_cat(bmi: float) -> int:
    if bmi < 18.5: return 0
    if bmi < 25.0: return 1
    if bmi < 30.0: return 2
    return 3

def _bp_stage(sys_bp: float, dia_bp: float) -> int:
    if sys_bp < 120 and dia_bp < 80: return 0
    if 120 <= sys_bp < 130 and dia_bp < 80: return 1
    if (130 <= sys_bp < 140) or (80 <= dia_bp < 90): return 2
    if sys_bp >= 180 or dia_bp >= 120: return 4
    return 3

def _safe_ratio(numer: float, denom: float) -> float:
    return float(numer) / float(denom if denom and denom > 1e-6 else 1e-6)

def _age(customer: Customer, fallback: Optional[int]) -> int:
    if fallback is not None:
        return int(fallback)
    dob = getattr(customer, "CustDOB", None)
    if dob:
        today = timezone.localdate()
        return int(today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day)))
    return 0

def _lab_to_features(lab: Patient_lab, cust: Customer) -> List[float]:
    age = _age(cust, getattr(lab, "Age", None))
    bmi = float(lab.BMI or 26.0)
    sys_bp = float(lab.Systolic_BP or 125.0)
    dia_bp = float(lab.Diastolic_BP or 78.0)
    tchol = float(lab.Total_Cholesterol or 190.0)
    hdl = float(lab.HDL_Cholesterol or 50.0)
    ldl = float(lab.LDL_Cholesterol or 110.0)
    trig = float(lab.Triglycerides or 120.0)
    smoker = 1.0 if bool(getattr(lab, "Smoking_status", False)) else 0.0
    activity_num = float(_norm_activity(getattr(lab, "Physical_activity", None)))

    pulse = float(sys_bp - dia_bp)
    chol_hdl = _safe_ratio(tchol, hdl)
    non_hdl = float(tchol - hdl)
    bp_stage = float(_bp_stage(sys_bp, dia_bp))
    bmi_cat = float(_bmi_cat(bmi))

    return [
        float(age), bmi, sys_bp, dia_bp,
        tchol, hdl, ldl, trig,
        smoker, activity_num,
        pulse, chol_hdl, non_hdl,
        bp_stage, bmi_cat,
    ]

# -----------------------
# Rule-based fallback
# -----------------------

def _rule_based_score(X: np.ndarray) -> np.ndarray:
    idx = {name: i for i, name in enumerate(FEATURE_NAMES)}
    z = (
        0.15 * (X[:, idx["BMI"]] / 30.0) +
        0.15 * (X[:, idx["Systolic_BP"]] / 140.0) +
        0.10 * (X[:, idx["Diastolic_BP"]] / 90.0) +
        0.15 * (X[:, idx["Chol_HDL_Ratio"]] / 5.0) +
        0.10 * (X[:, idx["Triglycerides"]] / 200.0) +
        0.20 * (X[:, idx["Smoking_status"]]) +
        0.05 * (X[:, idx["BP_Stage"]] / 4.0) +
        0.10 * (X[:, idx["BMI_Cat"]] / 3.0)
    )
    return 1.0 / (1.0 + np.exp(-z))

def _band(score: float) -> str:
    if score < 0.20: return "Low"
    if score < 0.50: return "Med"
    return "High"

# -----------------------
# (Optional) supervised model cache
# -----------------------

_PIPE = None  # trained sklearn pipeline cached in-process

def invalidate_model_cache():
    global _PIPE
    _PIPE = None

def _train_pipeline_if_labels() -> Optional[object]:
    """
    Train a simple scaler+logreg pipeline if labels exist.
    Cached thereafter until invalidated by label changes.
    """
    global _PIPE
    if _PIPE is not None:
        return _PIPE
    if not HAVE_LABELS:
        return None

    # Join latest lab per patient to labels
    from django.db.models import Max
    latest_ids = (
        Patient_lab.objects.values("Patient_id")
        .annotate(max_id=Max("id"))
        .values_list("max_id", flat=True)
    )
    labs = list(Patient_lab.objects.filter(id__in=list(latest_ids)).select_related("Patient_id"))

    X, y = [], []
    labels_map = {r.Patient_id_id: int(r.Label) for r in DiabetesOutcome.objects.all()}
    for lab in labs:
        lbl = labels_map.get(lab.Patient_id_id)
        if lbl is None:
            continue
        X.append(_lab_to_features(lab, lab.Patient_id))
        y.append(lbl)
    if not X or len(set(y)) < 2:
        return None

    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import LogisticRegression

    pipe = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])
    pipe.fit(np.asarray(X, dtype=float), np.asarray(y, dtype=int))
    _PIPE = pipe
    return _PIPE

# -----------------------
# Public API
# -----------------------

@transaction.atomic
def score_patient_now(patient_id: int) -> float:
    """
    Fetch latest Patient_lab for the given patient, score immediately,
    and write a RiskScore row. Returns the score.
    """
    lab = (
        Patient_lab.objects
        .filter(Patient_id_id=patient_id)
        .order_by("-id")
        .select_related("Patient_id")
        .first()
    )
    if not lab:
        return 0.0  # nothing to score

    x = np.asarray([_lab_to_features(lab, lab.Patient_id)], dtype=float)

    pipe = _train_pipeline_if_labels()
    if pipe is not None:
        score = float(pipe.predict_proba(x)[:, 1][0])
    else:
        score = float(_rule_based_score(x)[0])

    Risk_Score.objects.create(
        Patient_id=lab.Patient_id,
        Score=score,
        Band=_band(score),
        Score_date=timezone.now(),
    )
    return score

def retrain_async_hint():
    """
    Called when labels change; here we simply invalidate the cache.
    On next scoring call, a fresh model will be trained.
    """
    invalidate_model_cache()
