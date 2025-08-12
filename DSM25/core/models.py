
from django.db import models
from django.utils import timezone

# Create your models here.
class Customer(models.Model):
    Cust_id = models.AutoField(primary_key=True)
    CustFirstName = models.CharField(max_length=50)
    CustLastName = models.CharField(max_length=50)
    CustMiddleInit = models.CharField(max_length=1)
    CustSuffix = models.CharField(max_length=10)
    CustDOB = models.DateField(null=True, blank=True)
    Gender = models.CharField(max_length=10)
    CustomerType = models.CharField(max_length=50,null=True, blank=True)

class Patient_lab(models.Model):
    Patient_id = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    Age = models.IntegerField()
    BMI = models.FloatField()
    Systolic_BP = models.FloatField()
    Diastolic_BP = models.FloatField()
    Total_Cholesterol = models.FloatField()
    HDL_Cholesterol = models.FloatField()
    LDL_Cholesterol = models.FloatField()
    Triglycerides = models.FloatField()
    Smoking_status = models.BooleanField()
    Physical_activity = models.CharField(max_length=50)

class Clinical_note(models.Model):
    Patient_id = models.ForeignKey(Customer, on_delete=models.CASCADE,  null=True, blank=True)
    Description = models.TextField()
    Medical_specialty = models.CharField(max_length=100)
    Sample_name = models.CharField(max_length=100)
    Transcription = models.TextField()
    Keywords = models.TextField()

class Risk_FeatureSnapshot(models.Model):
    Patient_id = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    Age = models.IntegerField()
    BMI = models.FloatField()
    Systolic_BP = models.FloatField()
    Diastolic_BP = models.FloatField()
    Total_Cholesterol = models.FloatField()
    HDL_Cholesterol = models.FloatField()
    LDL_Cholesterol = models.FloatField()
    Triglycerides = models.FloatField()
    Smoking_status = models.BooleanField()
    Physical_activity = models.CharField(max_length=50)
    Observed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=['Patient_id', '-Observed_at']),
        ]

class Risk_Score(models.Model):
    Patient_id = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    Score = models.FloatField()
    Model_name = models.CharField(max_length=50, default='diabetes_risk')
    Model_version = models.CharField(max_length=20, default='v1.0')
    Band = models.CharField(max_length=20, null=True, blank=True)
    Score_date = models.DateTimeField(default=timezone.now)
    class Meta:
        indexes = [
            models.Index(fields=['Patient_id', '-Score']),
        ]

class DiabetesOutcome(models.Model):
    Patient_id = models.ForeignKey(Customer, on_delete=models.CASCADE)
    Label = models.BooleanField()
    Index_date = models.DateField(null=True, blank=True)   # reference date
    Horizon_days = models.IntegerField(default=180)        # 6 months by default
    Created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["Patient_id", "-Created_at"]),
            models.Index(fields=["Index_date"]),
        ]
        # To prevent duplicates per (patient, date, horizon), uncomment:
        constraints = [
            models.UniqueConstraint(
                fields=["Patient_id", "Index_date", "Horizon_days"],
                name="uniq_patient_date_horizon"
            )
        ]

    def __str__(self):
        return f"Outcome(p={self.Patient_id_id}, y={int(self.Label)}, t0={self.Index_date}, H={self.Horizon_days})"


class Note_prediction(models.Model):
    Note_id = models.ForeignKey(Clinical_note, on_delete=models.CASCADE, null=True, blank=True)
    Model_name = models.CharField(max_length=50, default='diabetes_risk')
    Model_version = models.CharField(max_length=20, default='v1.0')
    Prediction_specialty = models.CharField(max_length=100, null=True, blank=True)
    Confidence = models.FloatField(null=True, blank=True)
    Predicted_at = models.DateTimeField(default=timezone.now)
    class Meta:
        indexes = [
            models.Index(fields=['Note_id', '-Predicted_at']),
        ]
        unique_together = (('Note_id','Model_name', 'Model_version'),)
