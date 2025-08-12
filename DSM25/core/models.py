
from django.db import models

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

    class Meta:
        indexes = [
            models.Index(fields=['Patient_id']),
        ]

class Risk_Score(models.Model):
    Patient_id = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    Score = models.FloatField()
    Model_name = models.CharField(max_length=50, default='diabetes_risk')
    Model_version = models.CharField(max_length=20, default='v1.0')
    class Meta:
        indexes = [
            models.Index(fields=['Patient_id']),
        ]

class ModelRegistry(models.Model):
    Patient_id = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    Model_name = models.CharField(max_length=50, default='diabetes_risk')
    Model_version = models.CharField(max_length=20, default='v1.0')
    auc = models.FloatField(null=True, blank=True)
    pr_auc = models.FloatField(null=True, blank=True)
    class Meta:
        unique_together = (('Model_name', 'Model_version'),)
