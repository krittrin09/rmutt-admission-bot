from django.urls import path
from . import views

urlpatterns = [
    path("", views.criteria_home, name="criteria_home"),
]
