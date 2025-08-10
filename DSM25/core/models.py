from django.db import models

# Create your models here.
class Customer(models.Model):
    Cust_ID = models.AutoField(primary_key=True)
    CustFirstName = models.CharField(max_length=50)
    CustLastName = models.CharField(max_length=50)
    CustMiddleInit = models.CharField(max_length=1)
    CustSuffix = models.CharField(max_length=10)
    CustDOB = models.DateField()
    Gender = models.CharField(max_length=10)
    CustomerType = models.CharField(max_length=50)

