from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import os
import logging
from datetime import datetime
import re

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
@login_required
@user_passes_test(lambda u: u.is_superuser)
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
                # ===== ดึงชื่อสาขาแทนชื่อมหาลัย =====
                topic = ""
                lines = item.split("\n")

                for line in lines:
                    clean = line.strip()

                    if "สาขาวิชา:" in clean:
                        topic = clean.replace("สาขาวิชา:", "").strip()
                        break

                    if "หลักสูตร:" in clean:
                        topic = clean.replace("หลักสูตร:", "").strip()
                        break

                # fallback ถ้าไม่มีจริง ๆ
                if not topic:
                    topic_line = item.strip().split("\n")[0].replace("#", "").strip()
                    topic = topic_line.replace("มหาวิทยาลัย:", "").strip()


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
                # แปลงปีทั้งหมดเป็น พ.ศ. ก่อนบันทึก
                final_content = to_buddhist_year(final_content)

                os.makedirs(os.path.dirname(overview_path), exist_ok=True)

                with open(overview_path, "w", encoding="utf-8") as f:
                    f.write(final_content)

                ok = create_vector_db()
                if ok:
                    messages.success(request, "✅ บันทึกข้อมูลและอัปเดต RAG สำเร็จ")
                    request.session.pop("preview_list_cache", None)
                else:
                    messages.warning(request, "⚠️ บันทึกไฟล์สำเร็จ แต่สร้าง Vector DB ไม่สำเร็จ")

            except Exception as e:
                logger.exception(e)
                messages.error(request, f"❌ บันทึกไม่สำเร็จ: {e}")

            return redirect("manage_criteria")

    return render(request, "manage_criteria.html", context)
