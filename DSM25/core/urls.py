from django.urls import path,include 
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('management/', views.management, name='management'),
    path('import_data/', views.import_data, name='import_data'),
    path('score_diabetes/', views.run_score_diabetes, name='score_diabetes'),
    path('note_classifier/', views.run_note_classifier, name='note_classifier'),
]