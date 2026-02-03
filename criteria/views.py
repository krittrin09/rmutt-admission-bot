from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# --- Import RAG System ---
try:
    from chatbot.rag.ingest import create_vector_db
    from chatbot.rag.excel_parser import generate_tcas_rag_data
except ImportError as e:
    logger.error(f"❌ Import RAG error: {e}")


# ==============================
# Helper
# ==============================
def get_round_display_name(code):
    # Mapping ให้ตรงกับ RAG Engine
    mapping = {
        '1_2568': 'รอบที่ 1 Portfolio',
        '2_2568': 'รอบที่ 2 Quota',
        '3_2568': 'รอบที่ 3 Admission',
        '4_2568': 'รอบที่ 4 Direct Admission',
        'MOU': 'รอบที่ 1.2 Portfolio (MOU)', # เพิ่ม key สำหรับ MOU
    }
    # ถ้า code เป็นชื่อเต็มอยู่แล้วก็ใช้เลย
    if code in mapping.values():
        return code
    return mapping.get(code, "ข้อมูลทั่วไป")

# ==============================
# MAIN VIEW
# ==============================
@login_required
@user_passes_test(lambda u: u.is_superuser)
def manage_criteria(request):
    overview_path = os.path.join(
        settings.BASE_DIR, "chatbot", "rag", "data", "overview.txt"
    )

    # ★★★ 1. กำหนดลำดับรอบที่ต้องการให้แสดงเสมอ (เรียงซ้ายไปขวา) ★★★
    ALL_ROUNDS = [
        "รอบที่ 1 Portfolio",
        "รอบที่ 1.2 Portfolio (MOU)", 
        "รอบที่ 2 Quota",
        "รอบที่ 3 Admission",
        "รอบที่ 4 Direct Admission"
    ]

    # เตรียม Dict ว่างไว้ก่อน (เพื่อให้ Tab ขึ้นครบ)
    preview_data = {r: [] for r in ALL_ROUNDS}

    # ------------------------------------------------------------------
    # 1. LOAD DATA (PRIORITY: Session > Existing File)
    # ------------------------------------------------------------------
    session_data = request.session.get("preview_list_cache")

    if session_data:
        # กรณีมีข้อมูลจากการอัปโหลด Excel (อยู่ใน Session)
        # ให้ merge เข้าไปใน preview_data เพื่อรักษาลำดับ Key
        for r_name, items in session_data.items():
            # แปลงชื่อรอบให้ตรงกับ Standard Key
            standard_name = r_name
            if "MOU" in r_name.upper(): standard_name = "รอบที่ 1.2 Portfolio (MOU)"
            elif "4" in r_name: standard_name = "รอบที่ 4 Direct Admission"
            
            # ใส่ข้อมูลลงใน Key ที่ถูกต้อง
            if standard_name in preview_data:
                preview_data[standard_name] = items
            else:
                # กรณีชื่อรอบไม่ตรง (เช่น ข้อมูลทั่วไป) ให้ใส่ไว้ท้ายสุด หรือสร้าง key ใหม่
                preview_data.setdefault(standard_name, []).extend(items)

    elif os.path.exists(overview_path):
        # กรณีไม่มี Session ให้โหลดจากไฟล์เก่า (overview.txt)
        try:
            with open(overview_path, "r", encoding="utf-8") as f:
                content = f.read()

            raw_items = content.split("\n\n---\n\n")
            
            for item in raw_items:
                if not item.strip(): continue

                # Logic เดารอบจากเนื้อหา
                round_name = "ข้อมูลทั่วไป" 
                
                if "MOU" in item or "mou" in item.lower():
                     round_name = "รอบที่ 1.2 Portfolio (MOU)"
                else:
                    for r in ALL_ROUNDS:
                        if r in item: 
                            round_name = r
                            break
                        # เช็คแบบย่อ
                        if r.split()[0] + " " + r.split()[1] in item: 
                             round_name = r
                             break
                
                topic_line = item.strip().split("\n")[0].replace("#", "").strip()
                topic = topic_line.replace("หลักสูตร:", "").strip() # Clean topic

                # ดึงวันที่ (ปรับแก้ตาม Requirement ใหม่: --)
                start_date, end_date, interview_date = "", "", ""
                lines = item.split('\n')
                for line in lines:
                    # รองรับทั้งแบบเก่า ** และแบบใหม่ --
                    clean_line = line.replace("**", "").replace("--", "").strip()
                    
                    if "ช่วงเวลาการรับสมัคร:" in clean_line:
                        parts = clean_line.replace("ช่วงเวลาการรับสมัคร:", "").split("ถึง")
                        if len(parts) > 0: start_date = parts[0].strip()
                        if len(parts) > 1: end_date = parts[1].strip()
                    
                    if "วันที่:" in clean_line and "กำหนดการสัมภาษณ์" not in clean_line:
                        interview_date = clean_line.replace("วันที่:", "").replace("-", "").strip()

                item_id = str(hash(topic))[-6:]
                data_obj = {
                    "id": item_id,
                    "major_name": topic,
                    "content": item.strip(),
                    "start_date": start_date,
                    "end_date": end_date,
                    "interview_date": interview_date
                }
                
                if round_name in preview_data:
                    preview_data[round_name].append(data_obj)
                else:
                    preview_data.setdefault(round_name, []).append(data_obj)

        except Exception as e:
            logger.error(f"❌ Read overview error: {e}")

    context = {
        "preview_data": preview_data,
        "last_updated": "ไม่มีข้อมูล"
    }

    if os.path.exists(overview_path):
        ts = os.path.getmtime(overview_path)
        context["last_updated"] = datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M:%S")

    # ------------------------------------------------------------------
    # 2. POST HANDLER
    # ------------------------------------------------------------------
    if request.method == "POST":

        # A) UPLOAD EXCEL
        if "action_upload_excel" in request.POST:
            excel_file = request.FILES.get("excel_file")

            if not excel_file:
                messages.warning(request, "⚠️ กรุณาเลือกไฟล์ Excel")
                return redirect("manage_criteria")

            fs = FileSystemStorage()
            if fs.exists(excel_file.name):
                fs.delete(excel_file.name)

            filename = fs.save(excel_file.name, excel_file)
            uploaded_file_path = fs.path(filename)

            try:
                parsed_items = generate_tcas_rag_data(uploaded_file_path)

                if not parsed_items:
                    messages.warning(request, "⚠️ ไม่พบข้อมูลที่นำไปใช้กับ RAG ได้")
                    return redirect("manage_criteria")

                grouped = {}
                for item in parsed_items:
                    r_code = item.get("round", "")
                    # แปลง Code เป็นชื่อเต็ม (เช่น 1_2568 -> รอบที่ 1...)
                    r_name = get_round_display_name(r_code)
                    
                    # ถ้าชื่อสาขามีคำว่า MOU ให้ยัดลงรอบ MOU
                    if "MOU" in item.get("major_name", "").upper():
                        r_name = "รอบที่ 1.2 Portfolio (MOU)"

                    grouped.setdefault(r_name, []).append(item)

                # Save to Session
                request.session["preview_list_cache"] = grouped
                request.session.modified = True

                messages.success(request, f"✅ วิเคราะห์ข้อมูลสำเร็จ ({len(parsed_items)} รายการ)")

            except Exception as e:
                logger.exception(e)
                messages.error(request, f"❌ ประมวลผลล้มเหลว: {e}")

            finally:
                if os.path.exists(uploaded_file_path):
                    os.remove(uploaded_file_path)

            return redirect("manage_criteria")

        # B) SAVE DATA
        if "action_save_form" in request.POST:
            final_content = request.POST.get("rag_text_edit", "").strip()

            if not final_content:
                messages.warning(request, "⚠️ ไม่มีเนื้อหาให้บันทึก")
                return redirect("manage_criteria")

            try:
                # ปรับแก้ Format วันที่ก่อนบันทึก (เปลี่ยน ** เป็น --)
                # (Optional: ถ้าใน JS จัดการแล้ว ส่วนนี้อาจไม่จำเป็น แต่ทำกันเหนียวไว้)
                final_content = final_content.replace("**ช่วงเวลาการรับสมัคร:**", "-- ช่วงเวลาการรับสมัคร:")
                
                os.makedirs(os.path.dirname(overview_path), exist_ok=True)

                with open(overview_path, "w", encoding="utf-8") as f:
                    f.write(final_content)

                ok = create_vector_db()
                if ok:
                    messages.success(request, "✅ บันทึกข้อมูลและอัปเดต RAG สำเร็จ")
                    request.session.pop("preview_list_cache", None) # Clear Session
                else:
                    messages.warning(request, "⚠️ บันทึกไฟล์สำเร็จ แต่สร้าง Vector DB ไม่สำเร็จ")

            except Exception as e:
                logger.exception(e)
                messages.error(request, f"❌ บันทึกไม่สำเร็จ: {e}")

            return redirect("manage_criteria")

    return render(request, "manage_criteria.html", context)