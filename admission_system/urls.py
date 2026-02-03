from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from chatbot import views as chat_views

urlpatterns = [
    path("admin/", admin.site.urls),

    # หน้าแรกไปหน้าแชท
    path("", chat_views.chat_ui, name="home"),

    # apps
    path("ocr/", include("ocr_app.urls")),
    path("chatbot/", include("chatbot.urls")),
    path("admissions/", include("admissions.urls")),
    path("criteria/", include("criteria.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
