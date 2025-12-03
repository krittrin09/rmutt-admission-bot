from django.urls import path
from . import views

urlpatterns = [
    # หน้าหลัก
    path('', views.chat_ui, name='chat_ui'),
    
    # API สำหรับคุยกับบอท
    path('api/chat/', views.chat_api, name='chat_api'),
    
    # ✅ ลิ้งค์สำหรับปุ่ม Reset
    path('reset/', views.reset_chat, name='reset_chat'),
]