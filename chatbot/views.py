from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .rag.rag_engine import get_rag_chain

def chat_ui(request):
    # ลบ flush() ออกเพื่อให้จำชื่อได้
    return render(request, "chat.html")

def reset_chat(request):
    request.session.flush()
    return redirect("/")

@csrf_exempt
def chat_api(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)

    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()

        if not user_message:
            return JsonResponse({'response': 'กรุณาพิมพ์คำถาม'})

        # 1. โหลด Chain
        qa_chain = get_rag_chain() 
        if not qa_chain:
            return JsonResponse({'response': 'ระบบกำลังปรับปรุงฐานข้อมูล (กรุณารัน Ingest)'})

        # 2. ดึงข้อมูลนักเรียนจาก Session
        student_data = request.session.get('student_data', 'ผู้ใช้ยังไม่ได้อัปโหลดใบเกรด (ตอบตามเกณฑ์ทั่วไป)')

        # 3. ✅ "มัดรวม" ข้อมูลเกรด + คำถาม เป็นก้อนเดียว
        combined_query = f"""
        [ข้อมูลนักเรียนจากใบ ปพ.1]:
        {student_data}

        [คำถามจากผู้ใช้]:
        {user_message}
        """

        # 4. ส่งไปแค่ "query" (ตัวเดียวจบ ไม่ error แน่นอน)
        result = qa_chain.invoke({"query": combined_query})

        if isinstance(result, dict):
            bot_response = result.get('result') or result.get('answer') or ''
        else:
            bot_response = str(result)

        return JsonResponse({'response': bot_response})

    except Exception as e:
        print("Chat Error:", e)
        return JsonResponse({'response': f'เกิดข้อผิดพลาดระบบ: {str(e)}'}, status=500)