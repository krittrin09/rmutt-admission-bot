from django.urls import path
from . import views

urlpatterns = [
    # ... เส้นทางเดิมของคุณ (เช่น chat_ui, chat_api) ...
    path('', views.chat_ui, name='chat_ui'),  # ตัวอย่าง
    path('api/chat/', views.chat_api, name='chat_api'), # ตัวอย่าง
    path('reset/', views.reset_chat, name='reset_chat'), # ตัวอย่าง

    # ★★★ เพิ่ม 2 บรรทัดนี้ครับ ★★★
    path('api/extract_ocr/', views.extract_ocr, name='extract_ocr'),
    path('api/save_student_data/', views.save_student_data, name='save_student_data'),
    path('api/run_back_ocr/', views.run_back_ocr, name='run_back_ocr'),
    path('api/run_front_ocr/', views.run_front_ocr, name='run_front_ocr'),
]