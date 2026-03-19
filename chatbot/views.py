# chatbot/views.py
import json
import os
import logging
import re
import time
from datetime import datetime

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.conf import settings
from django.core.files.storage import FileSystemStorage

# Import OCR Engine Service
from ocr_engine.service import run_back_ocr_from_image
from ocr_engine.service import run_front_ocr_from_image

# Import RAG Engine
from chatbot.rag.rag_engine import ask_balanced, reload_vector_db

logger = logging.getLogger(__name__)

def extract_gpax(text):
    match = re.search(r"\b([0-4]\.\d{1,2})\b", text)
    return match.group(1) if match else None

def is_admin(user):
    return user.is_superuser

# =====================================================
# Chat UI & Basic Views
# =====================================================
def chat_ui(request):
    return render(request, "chat.html")

def reset_chat(request):
    request.session.flush()
    return redirect("/")

# =====================================================
# Chat API (แก้ไขส่วนนี้)
# =====================================================
@csrf_exempt
def chat_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
        question = data.get("message", "").strip()

        if not question:
            return JsonResponse({"reply": "❌ กรุณาพิมพ์คำถาม"})

        history = request.session.get('chat_history', [])
        
        # ★★★ 1. ดึงข้อมูลนักเรียนจาก Session (ที่บันทึกไว้ตอนกด Save Data) ★★★
        student_data = request.session.get('student_data') 

        start_time = time.time()

        # ★★★ 2. ส่ง student_data เข้าไปใน RAG Engine ★★★
        answer = ask_balanced(question, history, student_data=student_data)

        elapsed = time.time() - start_time
        logger.info(f"[RAG] response time: {elapsed:.2f}s")

        if not answer or not answer.strip():
            answer = "📌 ไม่พบข้อมูลที่ตรงกับคำถามนี้จากระเบียบการที่มีอยู่ครับ"

        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})
        request.session['chat_history'] = history[-10:]

        return JsonResponse({"reply": answer.strip()})

    except Exception as e:
        logger.exception("Chat API error")
        return JsonResponse({"reply": "❌ ระบบขัดข้องชั่วคราว"}, status=500)

# =====================================================
# Upload & Save Data (OCR)
# =====================================================
def _to_str(x):
    return "" if x is None else str(x).strip()

def pick_area(areas, target_name: str):
    for row in areas:
        if (row.get("กลุ่มสาระการเรียนรู้") or "").strip() == target_name:
            return _to_str(row.get("ผลการเรียนเฉลี่ย")), _to_str(row.get("หน่วยกิตรวม"))
    return "", ""

def _deep_find_first_str(obj, key_candidates):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in key_candidates and isinstance(v, str) and v.strip():
                return v.strip()
        for v in obj.values():
            found = _deep_find_first_str(v, key_candidates)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _deep_find_first_str(item, key_candidates)
            if found:
                return found
    return ""

def front_json_name_school(front_json: dict) -> dict:
    root = front_json
    if isinstance(front_json, dict) and "parsed" in front_json:
        root = front_json["parsed"]

    def deep_find(obj, keys):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in keys and isinstance(v, str) and v.strip():
                    return v.strip()
            for v in obj.values():
                found = deep_find(v, keys)
                if found:
                    return found
        elif isinstance(obj, list):
            for item in obj:
                found = deep_find(item, keys)
                if found:
                    return found
        return ""

    first_name_keys = {"first_name", "firstname", "ชื่อ"}
    last_name_keys = {"last_name", "lastname", "ชื่อสกุล", "นามสกุล"}
    school_keys = {"school", "school_name", "โรงเรียน", "โรงเรียนเดิม"}

    first_name = deep_find(root, first_name_keys)
    last_name = deep_find(root, last_name_keys)
    school = deep_find(root, school_keys)

    full_name = ""
    if first_name or last_name:
        full_name = f"{first_name} {last_name}".strip()

    return {"name": full_name, "school": school}

def back_json_4_fields(back_json: dict) -> dict:
    parsed = back_json.get("parsed", {})
    areas = parsed.get("learning_areas", [])

    def norm(s: str) -> str:
        return (s or "").strip().lower()

    def to_str(x):
        return "" if x is None else str(x).strip()

    def find_area(keyword):
        for row in areas:
            name = row.get("กลุ่มสาระการเรียนรู้")
            if isinstance(name, str) and keyword in norm(name):
                return row
        return None

    def gpa_credit(row):
        if not row:
            return "", ""
        return (
            to_str(row.get("ผลการเรียนเฉลี่ย")),
            to_str(row.get("หน่วยกิตรวม"))
        )

    gpax_row = find_area("ผลการเรียนเฉลี่ยตลอดหลักสูตร")
    gpax = to_str(gpax_row.get("ผลการเรียนเฉลี่ย")) if gpax_row else ""

    math_row = find_area("คณิต")
    math_gpa, math_credit = gpa_credit(math_row)

    sci_row = find_area("วิทย")
    science_gpa, science_credit = gpa_credit(sci_row)

    eng_row = find_area("ภาษาต่างประเทศ")
    english_gpa, english_credit = gpa_credit(eng_row)

    return {
        "gpax": gpax,
        "math_gpa": math_gpa,
        "math_credit": math_credit,
        "science_gpa": science_gpa,
        "science_credit": science_credit,
        "english_gpa": english_gpa,
        "english_credit": english_credit,
    }

@csrf_exempt
def extract_ocr(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid Method"}, status=405)

    try:
        # 1) รับไฟล์ (ถ้ามี) + อ่าน session json paths (ถ้ามี)
        front_file = request.FILES.get("front_file")
        back_file  = request.FILES.get("back_file")

        front_json_path = request.session.get("last_front_json")
        back_json_path  = request.session.get("last_back_json")

        if (not front_file and not back_file) and (not front_json_path and not back_json_path):
            return JsonResponse({
                "success": False,
                "error": "กรุณารัน OCR (Front/Back) อย่างน้อย 1 ฝั่งก่อน แล้วค่อยกดเริ่มประมวลผล AI"
            }, status=400)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        full_path_f = None
        full_path_b = None

        # 2) Save new files
        if front_file:
            ext_f = os.path.splitext(front_file.name)[1]
            f_name = f"{timestamp}-F{ext_f}"
            path_front = os.path.join(settings.MEDIA_ROOT, "front")
            os.makedirs(path_front, exist_ok=True)
            fs_f = FileSystemStorage(location=path_front)
            saved_f = fs_f.save(f_name, front_file)
            full_path_f = fs_f.path(saved_f)
            request.session["last_front_file"] = full_path_f
            request.session.modified = True

        if back_file:
            ext_b = os.path.splitext(back_file.name)[1]
            b_name = f"{timestamp}-B{ext_b}"
            path_back = os.path.join(settings.MEDIA_ROOT, "back")
            os.makedirs(path_back, exist_ok=True)
            fs_b = FileSystemStorage(location=path_back)
            saved_b = fs_b.save(b_name, back_file)
            full_path_b = fs_b.path(saved_b)
            request.session["last_back_file"] = full_path_b
            request.session.modified = True

        # 3) Mock data base
        mock_data = {
            "name": "ทดสอบ ระบบ",
            "school": "โรงเรียนสาธิต",
            "gpax": "3.50",
            "study_plan": "วิทย์-คณิต",
            "math_gpa": "3.00", "math_credit": "12",
            "science_gpa": "3.00", "science_credit": "22",
            "english_gpa": "3.50", "english_credit": "6",
        }
        source = "mock"

        # 4) Load JSON & Override
        front_json = None
        back_json = None

        if back_json_path and os.path.exists(back_json_path):
            with open(back_json_path, "r", encoding="utf-8") as f:
                back_json = json.load(f)
            extracted_back = back_json_4_fields(back_json)
            for k, v in extracted_back.items():
                if v != "":
                    mock_data[k] = v
            source = "back_json"

        if front_json_path and os.path.exists(front_json_path):
            with open(front_json_path, "r", encoding="utf-8") as f:
                front_json = json.load(f)
            extracted_front = front_json_name_school(front_json)
            if extracted_front.get("name"):
                mock_data["name"] = extracted_front["name"]
            if extracted_front.get("school"):
                mock_data["school"] = extracted_front["school"]

            if source == "mock":
                source = "front_json"
            elif source == "back_json":
                source = "front+back_json"

        # 5) Return
        return JsonResponse({
            "success": True,
            "ocr_data": mock_data,
            "source": source,
            "front_json": front_json,
            "back_json": back_json,
        }, json_dumps_params={"ensure_ascii": False})

    except Exception as e:
        logger.error(f"Error in extract_ocr: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500, json_dumps_params={"ensure_ascii": False})

@csrf_exempt
def save_student_data(request):
    """บันทึกข้อมูลจริงที่ User แก้ไขแล้วลง Session"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # ★★★ บันทึกข้อมูลสำคัญลง Session เพื่อให้ chat_api เรียกใช้ ★★★
            request.session['student_data'] = data
            request.session['user_name'] = data.get('name', 'User')
            
            # Context string for history (optional but good for debugging)
            context_msg = (
                f"[DATA_START] "
                f"ชื่อ: {data.get('name')} โรงเรียน: {data.get('school')} "
                f"GPAX: {data.get('gpax')} "
                f"MATH_CREDIT: {data.get('math_credit')} MATH_GPA: {data.get('math_gpa')} "
                f"SCI_CREDIT: {data.get('science_credit')} SCI_GPA: {data.get('science_gpa')} "
                f"ENG_CREDIT: {data.get('english_credit')} ENG_GPA: {data.get('english_gpa')} "
                f"[DATA_END]"
            )
            
            history = request.session.get('chat_history', [])
            history.append({"role": "system", "content": context_msg})
            request.session['chat_history'] = history
            
            reply_msg = (
                f"✅ บันทึกข้อมูลของ **{data.get('name')}** เรียบร้อยครับ!\n"
                f"เกรดเฉลี่ย: **{data.get('gpax')}**\n\n"
                "น้องสามารถถามพี่ Gaku ได้เลยครับ เช่น:\n"
                "🔹 *เกรดเท่านี้ยื่นสาขาไหนได้บ้าง?*"
            )
            return JsonResponse({'success': True, 'reply': reply_msg})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'success': False, 'error': 'Invalid request'})

# =====================================================
# Admin Management
# =====================================================
@login_required
@user_passes_test(is_admin)
def manage_criteria(request):
    overview_path = os.path.join(settings.BASE_DIR, "chatbot", "rag", "data", "overview.txt")
    preview_data = {}

    if os.path.exists(overview_path):
        try:
            with open(overview_path, "r", encoding="utf-8") as f:
                content = f.read()
            raw_items = content.split("\n\n---\n\n")
            for item in raw_items:
                if not item.strip(): continue
                topic = item.strip().split("\n")[0].replace("#", "").strip()
                preview_data.setdefault("ข้อมูล", []).append({"major_name": topic, "content": item.strip()})
        except Exception as e:
            logger.error(f"Error: {e}")

    context = {
        "preview_data": preview_data,
        "last_updated": datetime.fromtimestamp(os.path.getmtime(overview_path)).strftime("%d/%m/%Y") if os.path.exists(overview_path) else "-",
        "raw_content": open(overview_path).read() if os.path.exists(overview_path) else ""
    }

    if request.method == "POST":
        if "action_save_form" in request.POST:
            final_content = request.POST.get("rag_text_edit")
            if final_content:
                os.makedirs(os.path.dirname(overview_path), exist_ok=True)
                with open(overview_path, "w", encoding="utf-8") as f:
                    f.write(final_content)
                reload_vector_db()
                messages.success(request, "บันทึกเรียบร้อย")
                return redirect("manage_criteria")

    return render(request, "manage_criteria.html", context)

@csrf_exempt
def run_front_ocr(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"}, status=405)

    try:
        front_upload = request.FILES.get("front_file")
        if not front_upload:
            return JsonResponse({"success": False, "error": "ไม่พบไฟล์ front_file"}, status=400)

        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        ext = os.path.splitext(front_upload.name)[1].lower()
        front_filename = f"{timestamp}-F{ext}"

        front_dir = os.path.join(settings.MEDIA_ROOT, "front")
        os.makedirs(front_dir, exist_ok=True)

        fs = FileSystemStorage(location=front_dir)
        saved_name = fs.save(front_filename, front_upload)
        full_front_path = fs.path(saved_name)

        # Run OCR
        ocr_result = run_front_ocr_from_image(full_front_path)

        # Save Result
        out_dir = os.path.join(settings.MEDIA_ROOT, "temp", "Front_json")
        os.makedirs(out_dir, exist_ok=True)
        json_filename = f"{timestamp}-F.json"
        json_full_path = os.path.join(out_dir, json_filename)

        with open(json_full_path, "w", encoding="utf-8") as f:
            json.dump(ocr_result, f, ensure_ascii=False, indent=2)

        request.session["last_front_file"] = full_front_path
        request.session["last_front_json"] = json_full_path

        return JsonResponse({
            "success": True,
            "front_saved_path": full_front_path,
            "json_saved_path": json_full_path,
            "ocr_result": ocr_result,
        }, json_dumps_params={"ensure_ascii": False})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500, json_dumps_params={"ensure_ascii": False})

@csrf_exempt
def run_back_ocr(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid method"}, status=405)

    try:
        back_upload = request.FILES.get("back_file")
        if not back_upload:
            return JsonResponse({"success": False, "error": "ไม่พบไฟล์ back_file"}, status=400)

        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        ext = os.path.splitext(back_upload.name)[1].lower()
        back_filename = f"{timestamp}-B{ext}"

        back_dir = os.path.join(settings.MEDIA_ROOT, "back")
        os.makedirs(back_dir, exist_ok=True)

        fs = FileSystemStorage(location=back_dir)
        saved_name = fs.save(back_filename, back_upload)
        full_back_path = fs.path(saved_name)

        # Run OCR
        ocr_result = run_back_ocr_from_image(full_back_path)

        # Save Result
        out_dir = os.path.join(settings.MEDIA_ROOT, "temp", "Back_json")
        os.makedirs(out_dir, exist_ok=True)
        json_filename = f"{timestamp}-B.json"
        json_full_path = os.path.join(out_dir, json_filename)

        with open(json_full_path, "w", encoding="utf-8") as f:
            json.dump(ocr_result, f, ensure_ascii=False, indent=2)

        request.session["last_back_file"] = full_back_path
        request.session["last_back_json"] = json_full_path

        return JsonResponse({
            "success": True,
            "back_saved_path": full_back_path,
            "json_saved_path": json_full_path,
            "ocr_result": ocr_result,
        })

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)