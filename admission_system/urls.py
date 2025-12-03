from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# ✅ 1. เพิ่มบรรทัดนี้: ดึง View ของ Chatbot มาใช้
from chatbot import views as chat_views

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # ✅ 2. แก้บรรทัดนี้: ให้หน้าแรก ("") วิ่งไปหาหน้าแชททันที
    path("", chat_views.chat_ui, name='home'), 
    
    # (อันเก่าคือ core.urls เราไม่ใช้แล้ว หรือจะย้ายไป path อื่นก็ได้)
    # path("core/", include("core.urls")), 

    path("ocr/", include("ocr_app.urls")),
    path("admissions/", include("admissions.urls")),
    path("chatbot/", include("chatbot.urls")), # เก็บไว้สำหรับ API
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)