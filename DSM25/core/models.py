
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

class RiskScore(models.Model):
    Patient_id = models.ForeignKey(Customer, on_delete=models.CASCADE)
    Score = models.FloatField()             # 0..1 normalized risk score
    HighRisk = models.BooleanField(default=False)  # outcome label
    Scored_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["Patient_id", "-Scored_at"]),
            models.Index(fields=["HighRisk", "-Scored_at"]),
        ]

    def __str__(self):
        return f"RiskScore(patient={self.Patient_id_id}, score={self.Score:.3f}, high={self.HighRisk})"
