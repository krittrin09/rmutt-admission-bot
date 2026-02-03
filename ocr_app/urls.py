from django.urls import path
from . import views
from django.urls import path
from .views import ocr_back_view, test_ocr_page
from django.urls import path
from . import views

urlpatterns = [
    path("upload/", views.upload_view, name="ocr_upload"),
    path("confirm/", views.confirm_ocr_view, name="ocr_confirm"),
    path("ocr/back", ocr_back_view),
    path("test/ocr", test_ocr_page),
    path("api/ocr/back/", views.ocr_back_view, name="ocr_back_api"),
    path("api/extract-ocr/", views.extract_ocr,name="extract_ocr"),
    path("api/upload/", views.upload_front_back, name="upload_front_back"),
    path("api/ocr/back/run/", views.run_back_ocr_api, name="run_back_ocr_api"),
]