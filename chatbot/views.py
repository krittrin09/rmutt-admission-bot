from django.shortcuts import render
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt

# Import RAG Engine
# (ถ้าบรรทัดนี้ error ให้เช็คว่าไฟล์ rag_engine.py อยู่ถูกที่ไหม)
from .rag.rag_engine import get_rag_chain

def chat_ui(request):
    """
    ฟังก์ชันสำหรับแสดงหน้าจอ Chatbot (HTML)
    """
    return render(request, "chat.html")

def chat_api(request):
    """
    API สำหรับรับข้อความจาก JS และตอบกลับด้วย AI (RAG)
    """
    if request.method == 'POST':
        try:
            # 1. รับข้อความจาก JavaScript
            data = json.loads(request.body)
            user_message = data.get('message', '')

            # 2. เรียก RAG Engine
            qa_chain = get_rag_chain()
            
            if qa_chain:
                # ส่งคำถามไปให้ AI ตอบ
                result = qa_chain.invoke({"query": user_message})
                
                # ดึงเฉพาะคำตอบออกมา (รองรับทั้ง Dictionary และ String)
                if isinstance(result, dict):
                    bot_response = result.get('result', '')
                else:
                    bot_response = str(result)
            else:
                bot_response = "ขออภัย ระบบ RAG ยังไม่พร้อมใช้งาน (ไม่พบ Vector DB หรือโหลด Model ไม่ได้)"

            # 3. ส่งคำตอบกลับไปเป็น JSON
            return JsonResponse({'response': bot_response})

        except Exception as e:
            print(f"Chat Error: {e}")
            return JsonResponse({'response': f'เกิดข้อผิดพลาด: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Invalid method'}, status=400)