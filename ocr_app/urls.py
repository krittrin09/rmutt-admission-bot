from django.urls import path
from . import views

urlpatterns = [
    path("upload/", views.upload_view, name="ocr_upload"),
    path("confirm/", views.confirm_ocr_view, name="ocr_confirm"),
]
