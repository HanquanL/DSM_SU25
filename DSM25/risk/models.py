from django.db import models
from core.models import Customer


# Create your models here.
class Risk_score(models.Model):
    Patient_id = models.ForeignKey(Customer, on_delete=models.CASCADE)
    Risk_level = models.CharField(max_length=50)
    Score = models.FloatField()
    
