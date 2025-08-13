from django.urls import path,include 
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path("", include("risk.urls")),
    path("", include("note.urls")),
]