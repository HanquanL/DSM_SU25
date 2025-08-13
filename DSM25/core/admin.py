from django.contrib import admin
from .models import Customer, Patient_lab, Clinical_note

admin.site.register(Customer)
admin.site.register(Patient_lab)
admin.site.register(Clinical_note)
