from django.urls import path
from .views import triage_queue

urlpatterns = [ path("triage-queue/", triage_queue, name="triage_queue") ]
