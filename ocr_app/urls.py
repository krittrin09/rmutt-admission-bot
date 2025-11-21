from django.urls import path
from . import views

urlpatterns = [
    path("upload/", views.upload_view, name="ocr_upload"),
    path("result/<int:pk>/", views.result_view, name="ocr_result"),
]
