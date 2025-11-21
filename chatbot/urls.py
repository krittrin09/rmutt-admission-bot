from django.urls import path
from . import views

urlpatterns = [
    # หน้าแสดง UI (ใน iframe)
    path('', views.chat_ui, name='chat_ui'),  # หรือ views.chat_page แล้วแต่คุณตั้งชื่อ
    
    # API สำหรับรับส่งข้อความ (ที่ JavaScript จะยิงมา)
    path('api/', views.chat_api, name='chat_api'), 
]