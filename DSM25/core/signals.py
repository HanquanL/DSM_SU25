# core/signals.py
from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from core.models import Patient_lab

# Optional labels; if labels exist, retraining is triggered on change
try:
    from core.models import DiabetesOutcome
    HAVE_LABELS = True
except Exception:
    DiabetesOutcome = None
    HAVE_LABELS = False

# Import the scoring functions
from risk.risk_pipeline import score_patient_now, retrain_async_hint

@receiver(post_save, sender=Patient_lab)
def on_patient_lab_saved(sender, instance: Patient_lab, created, **kwargs):
    # Run AFTER the transaction commits so we don't read half-written rows.
    def _go():
        try:
            score_patient_now(instance.Patient_id_id)
        except Exception as e:
            # Keep silent/log as you prefer; we don't want to break saves.
            print(f"[signals] score_patient_now failed: {e}")
    transaction.on_commit(_go)

if HAVE_LABELS:
    @receiver(post_save, sender=DiabetesOutcome)
    def on_label_changed(sender, instance, created, **kwargs):
        # Invalidate cache; next score will retrain
        def _go():
            try:
                retrain_async_hint()
            except Exception as e:
                print(f"[signals] retrain hint failed: {e}")
        transaction.on_commit(_go)
