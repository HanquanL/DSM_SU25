from django.urls import path
from .views import risk_queue

urlpatterns = [
    path("diabetes_risk/", risk_queue, name="risk_queue"),
]
