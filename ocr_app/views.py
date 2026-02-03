# ocr_app/views.py
from django.shortcuts import redirect, render
from django.conf import settings
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from .utils.ocr import image_to_text
import os
import json
import re
import tempfile
from ocr_engine.service import run_back_ocr_from_image
from ocr_engine.service import run_back_ocr_from_temp_filename
from datetime import datetime


# =========================
# Helper Functions
# =========================
def extract_grade(text, keywords):
    for line in text.split('\n'):
        for key in keywords:
            if key in line:
                m = re.search(r'[0-4]\.\d{2}', line)
                if m:
                    return m.group(0)
    return ""

def extract_credit(text, keywords):
    for line in text.split('\n'):
        for key in keywords:
            if key in line:
                m = re.search(r'\d+(\.\d+)?', line)
                if m:
                    return m.group(0)
    return ""

def extract_plan(text):
    plans = [
        "วิทย์-คณิต", "วิทยาศาสตร์-คณิตศาสตร์",
        "ศิลป์-คำนวณ", "ศิลป์-ภาษา",
        "อาชีวศึกษา", "ปวช"
    ]
    for line in text.split('\n'):
        for p in plans:
            if p in line:
                return p
    return ""


# =========================
# OCR Upload
# =========================
@csrf_exempt
def upload_view(request):
    if request.method != "POST":
        return redirect("/")

    if not request.session.session_key:
        request.session.create()

    f = request.FILES.get("file")
    if not f:
        return JsonResponse({"status": "error", "message": "กรุณาเลือกไฟล์"})

    try:
        save_path = default_storage.save("transcripts/" + f.name, f)
        fullpath = os.path.join(settings.MEDIA_ROOT, save_path)

        text, lines = image_to_text(fullpath)

        # --- ชื่อ ---
        name = ""
        for l in lines:
            if "ชื่อ" in l and "สกุล" in l:
                name = l.replace("ชื่อ", "").replace("สกุล", "").replace(":", "").strip()
                break

        # --- ข้อมูลการเรียน ---
        data = {
            "name": name,
            "plan": extract_plan(text),
            "gpax": extract_grade(text, ["GPAX", "เฉลี่ยสะสม"]),
            "gpa_math": extract_grade(text, ["คณิต"]),
            "credit_math": extract_credit(text, ["คณิต"]),
            "gpa_sci": extract_grade(text, ["วิทย์"]),
            "credit_sci": extract_credit(text, ["วิทย์"]),
            "gpa_eng": extract_grade(text, ["อังกฤษ"]),
            "credit_eng": extract_credit(text, ["อังกฤษ"]),
        }

        # ✅ เก็บไว้ใน session ทันที (สำคัญมาก)
        request.session["ocr_data"] = data
        request.session["ocr_raw_text"] = text
        request.session.modified = True

        return JsonResponse({
            "status": "success",
            "data": data,
            "message": "อ่านข้อมูล OCR สำเร็จ"
        })

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})


# =========================
# Confirm OCR
# =========================
@csrf_exempt
def confirm_ocr_view(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid Method"})

    try:
        body = json.loads(request.body)

        # อัปเดตข้อมูลที่ผู้ใช้แก้ไข
        request.session["ocr_data"] = body.get("ocr_data")
        request.session["ocr_raw_text"] = body.get("raw_text")
        request.session.modified = True

        return JsonResponse({"status": "success"})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})

@csrf_exempt

def ocr_back_view(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "POST only"}, status=405)

    f = request.FILES.get("file") or request.FILES.get("image")
    if not f:
        return JsonResponse({"status": "error", "message": "missing file field: file/image"}, status=400)

    try:
        save_path = default_storage.save(f"uploads/{f.name}", ContentFile(f.read()))
        fullpath = os.path.join(settings.MEDIA_ROOT, save_path)

        # ✅ สั่งให้บันทึกไฟล์ลง Result_OCR
        result = run_back_ocr_from_image(fullpath, save_files=True)

        return JsonResponse(
            {"status": "success", "result": result},
            json_dumps_params={"ensure_ascii": False},
            status=200
        )

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


def test_ocr_page(request):
    return render(request, "test_ocr.html")

def upload_back_and_ocr(request):
    if request.method != "POST" or "file" not in request.FILES:
        return JsonResponse({"ok": False, "error": "No file"}, status=400)

    f = request.FILES["file"]

    # 1) save to media/temp (ใช้ชื่อที่ถูกเซฟจริง)
    rel_path = os.path.join("temp", f.name)
    saved_rel_path = default_storage.save(rel_path, ContentFile(f.read()))

    # 2) filename ที่ถูกต้อง (กรณีชื่อซ้ำระบบจะเปลี่ยนชื่อให้)
    filename = os.path.basename(saved_rel_path)

    # 3) OCR
    result = run_back_ocr_from_temp_filename(filename)

    return JsonResponse({"ok": True, "result": result}, json_dumps_params={"ensure_ascii": False})

@csrf_exempt

def extract_ocr(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST only"}, status=405)

    front_file = request.FILES.get("front_file")
    back_file = request.FILES.get("back_file")

    # ✅ ใหม่: ต้องมีอย่างน้อย 1 ไฟล์
    if not front_file and not back_file:
        return JsonResponse({"success": False, "error": "Missing front_file and back_file"}, status=400)

    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")

    front_rel_path = None
    back_rel_path = None

    # ✅ เซฟ front เฉพาะถ้ามี
    if front_file:
        ext_f = os.path.splitext(front_file.name)[1].lower()
        f_name = f"{timestamp}-F{ext_f}"
        front_rel_path = default_storage.save(f"front/{f_name}", front_file)

    # ✅ เซฟ back เฉพาะถ้ามี
    if back_file:
        ext_b = os.path.splitext(back_file.name)[1].lower()
        b_name = f"{timestamp}-B{ext_b}"
        back_rel_path = default_storage.save(f"back/{b_name}", back_file)

    # ✅ mock_data เดิม (ให้ popup เด้งเหมือนเดิม)
    mock_data = {
        "name": "ทดสอบ ระบบ",
        "school": "โรงเรียนสาธิต",
        "gpax": "3.50",
        "study_plan": "วิทย์-คณิต",
        "math_gpa": "3.00", "math_credit": "12",
        "science_gpa": "3.00", "science_credit": "22",
        "english_gpa": "3.50", "english_credit": "6",
    }

    return JsonResponse({
        "success": True,
        "front_rel_path": front_rel_path,
        "back_rel_path": back_rel_path,
        "ocr_data": mock_data,   # ✅ ส่ง mock กลับให้ popup ใช้
        "message": "Uploaded successfully (mock used)"
    }, json_dumps_params={"ensure_ascii": False})

@csrf_exempt  
def upload_front_back(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST only"}, status=405)

    front_file = request.FILES.get("front_file")
    back_file  = request.FILES.get("back_file")

    # ✅ รับไฟล์เดียวได้
    if not front_file and not back_file:
        return JsonResponse({"success": False, "error": "กรุณาอัปโหลดไฟล์อย่างน้อย 1 ด้าน"}, status=400)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    front_rel_path = None
    back_rel_path = None

    if front_file:
        ext_f = os.path.splitext(front_file.name)[1].lower()
        f_name = f"{timestamp}-F{ext_f}"
        front_rel_path = default_storage.save(f"front/{f_name}", front_file)

    if back_file:
        ext_b = os.path.splitext(back_file.name)[1].lower()
        b_name = f"{timestamp}-B{ext_b}"
        back_rel_path = default_storage.save(f"back/{b_name}", back_file)

    return JsonResponse({
        "success": True,
        "front_rel_path": front_rel_path,
        "back_rel_path": back_rel_path,
        "message": "Uploaded successfully"
    }, json_dumps_params={"ensure_ascii": False})

@csrf_exempt
def run_back_ocr_api(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST only"}, status=405)

    back_rel_path = request.POST.get("back_rel_path")
    if not back_rel_path:
        return JsonResponse({"success": False, "error": "Missing back_rel_path"}, status=400)

    # normalize + safety check
    back_rel_path = back_rel_path.replace("\\", "/")
    if not back_rel_path.startswith("back/"):
        return JsonResponse({"success": False, "error": "Invalid back_rel_path"}, status=400)

    back_full_path = os.path.join(settings.MEDIA_ROOT, back_rel_path)
    if not os.path.isfile(back_full_path):
        return JsonResponse({"success": False, "error": f"File not found: {back_rel_path}"}, status=404)

    try:
        # 1) run OCR + let pipeline save files to Result_OCR
        result = run_back_ocr_from_image(back_full_path, save_files=True)

        # 2) get saved json path from pipeline meta
        saved_json_path = (
            result.get("meta", {})
                  .get("saved_files", {})
                  .get("json")
        )

        if not saved_json_path:
            # pipeline did not report saved file path
            return JsonResponse({
                "success": False,
                "error": "Pipeline did not return meta.saved_files.json"
            }, status=500, json_dumps_params={"ensure_ascii": False})

        # 3) return only saved path (no extra saving here)
        return JsonResponse({
            "success": True,
            "back_rel_path": back_rel_path,
            "saved_json_path": saved_json_path
        }, json_dumps_params={"ensure_ascii": False})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500,
                            json_dumps_params={"ensure_ascii": False})

def run_front_ocr_api(request):
    # ยังไม่ทำ front OCR ตอนนี้ -> เอาไว้ทดสอบปุ่ม/เส้นทาง API ก่อน
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST only"}, status=405)

    front_rel_path = request.POST.get("front_rel_path", "")
    return JsonResponse({
        "success": True,
        "message": "Front OCR not enabled yet",
        "front_rel_path": front_rel_path,
    }, json_dumps_params={"ensure_ascii": False})