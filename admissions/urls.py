from django.urls import path
from .views import evaluate_view

urlpatterns = [path("evaluate/<int:pk>/", evaluate_view, name="admissions_evaluate")]
