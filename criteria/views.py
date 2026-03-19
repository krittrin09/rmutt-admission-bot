from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import os
import logging
from datetime import datetime
import re

# ★ 1. นำเข้า Model สิทธิ์ที่สร้างไว้
from .models import MajorPermission

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
    mapping = {
        '1_2568': 'รอบที่ 1 Portfolio',
        '2_2568': 'รอบที่ 2 Quota',
        '3_2568': 'รอบที่ 3 Admission',
        '4_2568': 'รอบที่ 4 Direct Admission',
        'MOU': 'รอบที่ 1.2 Portfolio (MOU)',
    }
    if code in mapping.values():
        return code
    return mapping.get(code, "ข้อมูลทั่วไป")


def to_buddhist_year(date_str):
    """
    แปลงปี ค.ศ. -> พ.ศ. อัตโนมัติ
    รองรับ:
    - dd/mm/yyyy
    - yyyy
    - ข้อความที่มีปี 4 หลัก
    """
    if not date_str:
        return date_str

    def repl(match):
        year = int(match.group())
        if year < 2400:  # ถ้าเป็น ค.ศ.
            return str(year + 543)
        return str(year)

    return re.sub(r'\b\d{4}\b', repl, date_str)


# ==============================
# MAIN VIEW
# ==============================
# ★ 2. ถอด @user_passes_test ออก เพื่อให้ User ทั่วไปเข้าหน้านี้ได้
@login_required
def manage_criteria(request):

    overview_path = os.path.join(
        settings.BASE_DIR, "chatbot", "rag", "data", "overview.txt"
    )

    ALL_ROUNDS = [
        "รอบที่ 1 Portfolio",
        "รอบที่ 1.2 Portfolio (MOU)",
        "รอบที่ 2 Quota",
        "รอบที่ 3 Admission",
        "รอบที่ 4 Direct Admission"
    ]

    preview_data = {r: [] for r in ALL_ROUNDS}

    # ★ 3. ดึงรายการสาขาที่ User ปัจจุบันมีสิทธิ์แก้ไข
    allowed_majors = []
    if not request.user.is_superuser:
        allowed_majors = list(MajorPermission.objects.filter(user=request.user).values_list('major_name', flat=True))

    # ------------------------------------------------------------------
    # LOAD DATA
    # ------------------------------------------------------------------
    session_data = request.session.get("preview_list_cache")

    if session_data:
        for r_name, items in session_data.items():
            standard_name = r_name
            if "MOU" in r_name.upper():
                standard_name = "รอบที่ 1.2 Portfolio (MOU)"
            elif "4" in r_name:
                standard_name = "รอบที่ 4 Direct Admission"

            # ★ 4. เช็คสิทธิ์ก่อนส่งข้อมูลขึ้นหน้าเว็บ (กรณีมีไฟล์ใน Session)
            for itm in items:
                itm['can_edit'] = request.user.is_superuser or (itm.get('major_name') in allowed_majors)

            if standard_name in preview_data:
                preview_data[standard_name] = items
            else:
                preview_data.setdefault(standard_name, []).extend(items)

    elif os.path.exists(overview_path):
        try:
            with open(overview_path, "r", encoding="utf-8") as f:
                content = f.read()

            raw_items = content.split("\n\n---\n\n")

            for item in raw_items:
                if not item.strip():
                    continue

                round_name = "ข้อมูลทั่วไป"

                if "MOU" in item or "mou" in item.lower():
                    round_name = "รอบที่ 1.2 Portfolio (MOU)"
                else:
                    for r in ALL_ROUNDS:
                        if r in item:
                            round_name = r
                            break
                            
                # ==========================================================
                # ★ แก้ไข: ลำดับการดึงชื่อสาขา ให้ยึด "สาขาวิชา:" เป็นหลักเสมอ
                # ==========================================================
                topic = ""
                lines = item.split("\n")

                # วนหาคำว่า "สาขาวิชา:" ก่อน
                for line in lines:
                    clean = line.strip()
                    if "สาขาวิชา:" in clean:
                        topic = clean.replace("สาขาวิชา:", "").strip()
                        break
                
                # ถ้าไม่เจอ "สาขาวิชา:" ค่อยไปหา "หลักสูตร:"
                if not topic:
                    for line in lines:
                        clean = line.strip()
                        if "หลักสูตร:" in clean:
                            topic = clean.replace("หลักสูตร:", "").strip()
                            break

                # fallback ถ้าไม่มีจริง ๆ
                if not topic:
                    topic_line = item.strip().split("\n")[0].replace("#", "").strip()
                    topic = topic_line.replace("มหาวิทยาลัย:", "").strip()
                # ==========================================================

                start_date, end_date, interview_date = "", "", ""
                lines = item.split('\n')

                for line in lines:
                    clean_line = line.replace("**", "").replace("--", "").strip()

                    if "ช่วงเวลาการรับสมัคร:" in clean_line:
                        parts = clean_line.replace("ช่วงเวลาการรับสมัคร:", "").split("ถึง")
                        if len(parts) > 0:
                            start_date = to_buddhist_year(parts[0].strip())
                        if len(parts) > 1:
                            end_date = to_buddhist_year(parts[1].strip())

                    if "วันที่:" in clean_line and "กำหนดการสัมภาษณ์" not in clean_line:
                        interview_date = clean_line.replace("วันที่:", "").replace("-", "").strip()
                        interview_date = to_buddhist_year(interview_date)

                item_id = str(hash(topic))[-6:]

                # ★ 5. ส่งตัวแปร can_edit ไปให้ HTML
                can_edit = request.user.is_superuser or (topic in allowed_majors)

                data_obj = {
                    "id": item_id,
                    "major_name": topic,
                    "content": item.strip(),
                    "start_date": start_date,
                    "end_date": end_date,
                    "interview_date": interview_date,
                    "can_edit": can_edit
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

    # last updated -> พ.ศ.
    if os.path.exists(overview_path):
        ts = os.path.getmtime(overview_path)
        dt = datetime.fromtimestamp(ts)
        year_be = dt.year + 543
        context["last_updated"] = dt.strftime(f"%d/%m/{year_be} %H:%M:%S")

    # ------------------------------------------------------------------
    # POST HANDLER
    # ------------------------------------------------------------------
    if request.method == "POST":

        # A) UPLOAD EXCEL
        if "action_upload_excel" in request.POST:
            # ★ 6. ป้องกัน: ให้เฉพาะ Superuser อัปโหลดไฟล์ได้
            if not request.user.is_superuser:
                messages.error(request, "⚠️ เฉพาะผู้ดูแลระบบ (Superuser) เท่านั้นที่สามารถอัปโหลดไฟล์ Excel ได้")
                return redirect("manage_criteria")

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
                    r_name = get_round_display_name(r_code)

                    if "MOU" in item.get("major_name", "").upper():
                        r_name = "รอบที่ 1.2 Portfolio (MOU)"

                    # บังคับปีเป็น พ.ศ.
                    item["start_date"] = to_buddhist_year(item.get("start_date", ""))
                    item["end_date"] = to_buddhist_year(item.get("end_date", ""))
                    item["interview_date"] = to_buddhist_year(item.get("interview_date", ""))

                    grouped.setdefault(r_name, []).append(item)

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
                # ★ 7. ระบบป้องกันหลังบ้าน: ใครไม่มีสิทธิ์ ห้ามเซฟทับ ให้ดึงข้อมูลเดิมจากไฟล์มาใส่แทน
                original_dict = {}
                if os.path.exists(overview_path):
                    with open(overview_path, "r", encoding="utf-8") as f:
                        orig_raw = f.read().split("\n\n---\n\n")
                        for block in orig_raw:
                            if not block.strip(): continue
                            
                            # ดึงชื่อสาขาด้วย Logic เดียวกับตอน Load
                            orig_topic = ""
                            for line in block.split("\n"):
                                clean = line.strip()
                                if "สาขาวิชา:" in clean:
                                    orig_topic = clean.replace("สาขาวิชา:", "").strip()
                                    break
                            
                            if not orig_topic:
                                for line in block.split("\n"):
                                    clean = line.strip()
                                    if "หลักสูตร:" in clean:
                                        orig_topic = clean.replace("หลักสูตร:", "").strip()
                                        break
                                        
                            if not orig_topic:
                                orig_topic = block.strip().split("\n")[0].replace("#", "").replace("มหาวิทยาลัย:", "").strip()
                                
                            original_dict[orig_topic] = block.strip()

                new_blocks = final_content.split("\n\n---\n\n")
                safe_blocks = []

                for block in new_blocks:
                    if not block.strip(): continue
                    
                    # ดึงชื่อสาขาจากข้อมูลที่เพิ่งส่งมา
                    new_topic = ""
                    for line in block.split("\n"):
                        clean = line.strip()
                        if "สาขาวิชา:" in clean:
                            new_topic = clean.replace("สาขาวิชา:", "").strip()
                            break
                    
                    if not new_topic:
                        for line in block.split("\n"):
                            clean = line.strip()
                            if "หลักสูตร:" in clean:
                                new_topic = clean.replace("หลักสูตร:", "").strip()
                                break
                                
                    if not new_topic:
                        new_topic = block.strip().split("\n")[0].replace("#", "").replace("มหาวิทยาลัย:", "").strip()

                    # ตรวจสอบสิทธิ์
                    if request.user.is_superuser or (new_topic in allowed_majors):
                        # มีสิทธิ์แก้ -> ใช้ข้อมูลใหม่ และแปลงปี พ.ศ. ให้ตามเดิมของคุณ
                        safe_blocks.append(to_buddhist_year(block.strip()))
                    else:
                        # ไม่มีสิทธิ์แก้ -> ดึงของเก่ากลับมาทับ!
                        if new_topic in original_dict:
                            safe_blocks.append(original_dict[new_topic])

                # ประกอบร่างกลับเป็น Text เหมือนเดิม
                safe_final_content = "\n\n---\n\n".join(safe_blocks)

                os.makedirs(os.path.dirname(overview_path), exist_ok=True)

                with open(overview_path, "w", encoding="utf-8") as f:
                    f.write(safe_final_content)

                ok = create_vector_db()
                if ok:
                    messages.success(request, "✅ บันทึกข้อมูลและอัปเดต RAG สำเร็จ (ระบบป้องกันการแก้ไขทำงานปกติ)")
                    request.session.pop("preview_list_cache", None)
                else:
                    messages.warning(request, "⚠️ บันทึกไฟล์สำเร็จ แต่สร้าง Vector DB ไม่สำเร็จ")

            except Exception as e:
                logger.exception(e)
                messages.error(request, f"❌ บันทึกไม่สำเร็จ: {e}")

            return redirect("manage_criteria")

    return render(request, "manage_criteria.html", context)