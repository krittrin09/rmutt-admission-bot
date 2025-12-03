from django.shortcuts import render, redirect
from django.conf import settings
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .utils.ocr import image_to_text, extract_fields_from_lines
import os
import json
import re
from chatbot.rag.rag_utils import create_vector_db_from_text

# --- Helper Functions ---
def extract_grade(text, keywords):
    lines = text.split('\n')
    for line in lines:
        for key in keywords:
            if key in line:
                match = re.search(r'[0-4]\.\d{2}', line)
                if match: return match.group(0)
    return ""

def extract_credit(text, keywords):
    lines = text.split('\n')
    for line in lines:
        for key in keywords:
            if key in line:
                match = re.search(r'\d+(\.\d+)?', line) 
                if match: return match.group(0)
    return ""

# ✅ ฟังก์ชันแกะแผนการเรียน
def extract_plan(text):
    keywords = ["วิทย์-คณิต", "วิทยาศาสตร์-คณิตศาสตร์", "Sci-Math", 
                "ศิลป์-คำนวณ", "ศิลป์-ภาษา", "ไทย-สังคม", "อาชีวศึกษา", "ปวช"]
    for line in text.split('\n'):
        for key in keywords:
            if key in line:
                return key
    return ""

@csrf_exempt
def upload_view(request):
    if request.method == "GET": return redirect("/")

    if request.method == "POST":
        if not request.session.session_key: request.session.create()
        
        f = request.FILES.get("file")
        if not f: return JsonResponse({"status": "error", "message": "กรุณาเลือกไฟล์"})

        try:
            save_path = default_storage.save("transcripts/" + f.name, f)
            fullpath = os.path.join(settings.MEDIA_ROOT, save_path)
            
            text, lines = image_to_text(fullpath)
            
            # 1. ชื่อ
            detected_name = ""
            for line in lines:
                if "ชื่อ" in line and "สกุล" in line:
                    detected_name = line.replace("ชื่อ", "").replace("นามสกุล", "").replace(":", "").strip()
                    break
            
            # 2. ✅ แผนการเรียน
            detected_plan = extract_plan(text)

            # 3. เกรด
            gpax = extract_grade(text, ["GPAX", "เฉลี่ยสะสม", "Cum. G.P.A."])
            gpa_math = extract_grade(text, ["คณิต", "MATH", "Mathematics"])
            credit_math = extract_credit(text, ["หน่วยกิตคณิต", "Credit Math"])
            gpa_sci = extract_grade(text, ["วิทย์", "SCI", "Science"])
            credit_sci = extract_credit(text, ["หน่วยกิตวิทย์", "Credit Science"])
            gpa_eng = extract_grade(text, ["อังกฤษ", "ENG", "English"])
            credit_eng = extract_credit(text, ["หน่วยกิตอังกฤษ", "Credit Eng"])

            return JsonResponse({
                "status": "review_needed",
                "data": {
                    "name": detected_name,
                    "plan": detected_plan,  # ✅ ส่งค่าแผนการเรียนกลับไป
                    "gpax": gpax,
                    "gpa_math": gpa_math, "credit_math": credit_math,
                    "gpa_sci": gpa_sci, "credit_sci": credit_sci,
                    "gpa_eng": gpa_eng, "credit_eng": credit_eng,
                    "raw_text": text
                },
                "message": "อ่านข้อมูลสำเร็จ"
            })

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})

    return JsonResponse({"status": "error", "message": "Method not allowed"})

@csrf_exempt
def confirm_ocr_view(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            # รับข้อมูล Text ก้อนใหญ่ที่รวมร่างแล้วจากหน้าบ้าน
            final_text = data.get("text", "")
            user_name = data.get("user_name", "")

            if not request.session.session_key: request.session.create()
            
            # บันทึกลง Session
            request.session['user_name'] = user_name
            request.session['student_data'] = final_text
            request.session.modified = True 
            
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
            
    return JsonResponse({"status": "error", "message": "Invalid Method"})