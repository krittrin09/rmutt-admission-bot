import os
import re
import logging
from datetime import datetime
from django.conf import settings

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaLLM

logger = logging.getLogger(__name__)

# =====================================================
# CONFIG
# =====================================================
DATA_FILE = os.path.join(settings.BASE_DIR, "chatbot", "rag", "data", "overview.txt")
MODEL_NAME = "qwen2.5:1.5b"

_VECTOR_DB = None
_EMBEDDINGS = None
_LLM = None
_LAST_MTIME = 0

ROUND_ORDER_MAP = {"Portfolio": 1, "Quota": 2, "Admission": 3, "Direct Admission": 4}
THAI_MONTHS = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]

# =====================================================
# INIT MODELS
# =====================================================
def get_embeddings():
    global _EMBEDDINGS
    if _EMBEDDINGS is None:
        _EMBEDDINGS = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    return _EMBEDDINGS

def get_llm():
    global _LLM
    if _LLM is None:
        _LLM = OllamaLLM(model=MODEL_NAME, temperature=0.3, num_ctx=8192, num_predict=4096)
    return _LLM

def load_vector_db():
    global _VECTOR_DB, _LAST_MTIME
    if not os.path.exists(DATA_FILE): return None
    current_mtime = os.path.getmtime(DATA_FILE)
    if _VECTOR_DB is None or current_mtime > _LAST_MTIME: reload_vector_db()
    return _VECTOR_DB

def reload_vector_db():
    global _VECTOR_DB, _LAST_MTIME
    try:
        embeddings = get_embeddings()
        with open(DATA_FILE, "r", encoding="utf-8") as f: text = f.read()
        docs = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150).create_documents([text])
        _VECTOR_DB = FAISS.from_documents(docs, embeddings)
        _LAST_MTIME = os.path.getmtime(DATA_FILE)
        return True
    except Exception as e:
        logger.error(f"DB Load Error: {e}")
        return False

# =====================================================
# HELPER FUNCTIONS (OCR & EXTRACTION)
# =====================================================

def safe_float(value):
    """ฟังก์ชันช่วยแปลงค่าเป็นตัวเลขทศนิยม ป้องกัน Error"""
    try:
        if not value: return 0.0
        # ลบ comma และช่องว่างออกก่อนแปลง
        clean_val = str(value).replace(",", "").strip()
        # หาเฉพาะตัวเลขและจุดทศนิยม (เผื่อมีตัวหนังสือติดมา)
        match = re.search(r"(\d+(\.\d+)?)", clean_val)
        if match:
            return float(match.group(1))
        return 0.0
    except (ValueError, TypeError):
        return 0.0

def get_student_profile(history, ocr_data=None):
    """
    ดึงข้อมูลนักเรียน:
    1. Priority สูงสุด: ดึงจาก ocr_data (ถ้ามีส่งเข้ามา)
    2. Priority รอง: ดึงจากประวัติแชท (history) ด้วย Regex ที่ยืดหยุ่น
    """
    profile = {
        "name": "น้อง", 
        "gpax": 0.0, 
        # เกรดเฉลี่ยรายวิชา
        "math_gpa": 0.0, "sci_gpa": 0.0, "eng_gpa": 0.0,
        # หน่วยกิต
        "math_credit": 0.0, "sci_credit": 0.0, "eng_credit": 0.0
    }

    # =========================================================
    # 1. กรณีมีข้อมูลจาก OCR (mock_data) ให้ใช้ก่อนเลย แม่นยำที่สุด
    # =========================================================
    if ocr_data and isinstance(ocr_data, dict):
        # ชื่อ
        profile["name"] = ocr_data.get("name", "น้อง")
        
        # GPAX
        profile["gpax"] = safe_float(ocr_data.get("gpax"))

        # เกรดรายวิชา (Map Key จาก ocr ให้ตรงกับระบบ)
        profile["math_gpa"] = safe_float(ocr_data.get("math_gpa"))
        profile["sci_gpa"]  = safe_float(ocr_data.get("science_gpa")) 
        profile["eng_gpa"]  = safe_float(ocr_data.get("english_gpa")) 

        # หน่วยกิต (Map Key จาก ocr ให้ตรงกับระบบ)
        profile["math_credit"] = safe_float(ocr_data.get("math_credit"))
        profile["sci_credit"]  = safe_float(ocr_data.get("science_credit"))
        profile["eng_credit"]  = safe_float(ocr_data.get("english_credit"))

        return profile # คืนค่าทันที ถ้ามี OCR แล้ว

    # =========================================================
    # 2. กรณีไม่มี OCR ให้หาจากประวัติแชท (History)
    # =========================================================
    if history:
        for msg in reversed(history):
            content = msg.get("content", "")
            
            # ตรวจสอบว่าข้อความนี้น่าจะมีข้อมูลหรือไม่
            if any(x in content for x in ["[DATA_START]", "ข้อมูล", "Profile", "Name", "ชื่อ", "GPA", "เกรด"]):
                
                # 1. ชื่อ (Name)
                if profile["name"] == "น้อง":
                    name_match = re.search(r"(?:ชื่อ|Name)[:\s]*([^\s\n]+)", content, re.IGNORECASE)
                    if name_match: profile["name"] = name_match.group(1)
                
                # 2. GPAX (เกรดเฉลี่ยรวม)
                if profile["gpax"] == 0:
                    gpax_match = re.search(r"(?:GPAX|เกรดเฉลี่ย|GPA)[^0-9]*?([\d]\.[\d]{1,2})", content, re.IGNORECASE)
                    if gpax_match: profile["gpax"] = float(gpax_match.group(1))

                # 3. หน่วยกิต (Credits) - Regex แบบกว้าง (Flexible)
                # คณิต
                if profile["math_credit"] == 0:
                    m_c = re.search(r"(?:หน่วยกิต|Credit|นก\.|Unit)[^0-9\n]*(?:คณิต|Math)[^0-9\n]*[:\s]*(\d+)", content, re.IGNORECASE)
                    if m_c: profile["math_credit"] = float(m_c.group(1))
                # วิทย์
                if profile["sci_credit"] == 0:
                    s_c = re.search(r"(?:หน่วยกิต|Credit|นก\.|Unit)[^0-9\n]*(?:วิทย์|Sci)[^0-9\n]*[:\s]*(\d+)", content, re.IGNORECASE)
                    if s_c: profile["sci_credit"] = float(s_c.group(1))
                # อังกฤษ
                if profile["eng_credit"] == 0:
                    e_c = re.search(r"(?:หน่วยกิต|Credit|นก\.|Unit)[^0-9\n]*(?:อังกฤษ|Eng|Foreign)[^0-9\n]*[:\s]*(\d+)", content, re.IGNORECASE)
                    if e_c: profile["eng_credit"] = float(e_c.group(1))

                # 4. เกรดรายวิชา (Subject GPA) - Regex แบบกว้าง
                # คณิต
                if profile["math_gpa"] == 0:
                    m_g = re.search(r"(?:เกรด|GPA|Grade)[^0-9\n]*(?:คณิต|Math)[^0-9\n]*[:\s]*([0-4]\.?\d*)", content, re.IGNORECASE)
                    if m_g: profile["math_gpa"] = float(m_g.group(1))
                # วิทย์
                if profile["sci_gpa"] == 0:
                    s_g = re.search(r"(?:เกรด|GPA|Grade)[^0-9\n]*(?:วิทย์|Sci)[^0-9\n]*[:\s]*([0-4]\.?\d*)", content, re.IGNORECASE)
                    if s_g: profile["sci_gpa"] = float(s_g.group(1))
                # อังกฤษ
                if profile["eng_gpa"] == 0:
                    e_g = re.search(r"(?:เกรด|GPA|Grade)[^0-9\n]*(?:อังกฤษ|Eng|Foreign)[^0-9\n]*[:\s]*([0-4]\.?\d*)", content, re.IGNORECASE)
                    if e_g: profile["eng_gpa"] = float(e_g.group(1))
                
                # ถ้าได้ข้อมูลสำคัญครบแล้ว (GPAX) ก็หยุดวนลูปได้
                if profile["gpax"] > 0 and profile["math_credit"] > 0:
                    break
            
    return profile

def extract_course_details(text):
    details = {}
    for r_key in ROUND_ORDER_MAP.keys():
        if r_key in text:
            details["round"] = r_key
            break
    if "round" not in details: details["round"] = "General"

    major_match = re.search(r"หลักสูตร:\s*(.+)", text)
    if major_match: details["major"] = major_match.group(1).strip()
    else: return None 

    # GPAX
    gpax_match = re.search(r"GPAX ขั้นต่ำ:\s*([\d\.]+)", text)
    details["min_gpax"] = float(gpax_match.group(1)) if gpax_match else 0.0

    # Seats
    seat_match = re.search(r"จำนวนรับ:\s*(\d+)", text)
    details["seats"] = int(seat_match.group(1)) if seat_match else 0

    # Subject Grades
    math_match = re.search(r"(?:เกรด|GPA|ผลการเรียน).*?คณิต.*?(?:ไม่ต่ำกว่า|ขั้นต่ำ|:|>=)\s*([\d\.]+)", text)
    details["min_math"] = float(math_match.group(1)) if math_match else 0.0

    sci_match = re.search(r"(?:เกรด|GPA|ผลการเรียน).*?วิทย.*?(?:ไม่ต่ำกว่า|ขั้นต่ำ|:|>=)\s*([\d\.]+)", text)
    details["min_sci"] = float(sci_match.group(1)) if sci_match else 0.0

    eng_match = re.search(r"(?:เกรด|GPA|ผลการเรียน).*?(?:อังกฤษ|ภาษาต่างประเทศ|Eng).*?(?:ไม่ต่ำกว่า|ขั้นต่ำ|:|>=)\s*([\d\.]+)", text)
    details["min_eng"] = float(eng_match.group(1)) if eng_match else 0.0

    # Date
    date_range = "-"
    range_match = re.search(r"ช่วงเวลาการรับสมัคร[:\s]*(.+)", text)
    if range_match:
        raw_date = range_match.group(1).strip()
        if re.search(r"\d{4}", raw_date): date_range = raw_date
    if date_range == "-":
        fallback_match = re.search(r"(?:รับสมัคร|วันที่)[:\s]*([0-9]{1,2}.*?[0-9]{4}.*?[0-9]{4})", text)
        if fallback_match: date_range = fallback_match.group(1).strip()
    details["date_range"] = date_range

    # Credits Requirement Extraction
    req_credits = {"math": 0, "sci": 0, "eng": 0, "text": "-"}
    credit_text_list = []
    
    if "หน่วยกิต" in text:
        math_c = re.search(r"หน่วยกิต.*?คณิต.*?(?:ไม่น้อยกว่า|>=)\s*(\d+)", text)
        if math_c: 
            val = int(math_c.group(1))
            req_credits["math"] = val
            credit_text_list.append(f"คณิต {val}")
        
        sci_c = re.search(r"หน่วยกิต.*?วิทย.*?(?:ไม่น้อยกว่า|>=)\s*(\d+)", text)
        if sci_c: 
            val = int(sci_c.group(1))
            req_credits["sci"] = val
            credit_text_list.append(f"วิทย์ {val}")

        eng_c = re.search(r"หน่วยกิต.*?(?:อังกฤษ|ภาษาต่างประเทศ|Eng).*?(?:ไม่น้อยกว่า|>=)\s*(\d+)", text)
        if eng_c: 
            val = int(eng_c.group(1))
            req_credits["eng"] = val
            credit_text_list.append(f"Eng {val}")
            
    if credit_text_list: req_credits["text"] = ", ".join(credit_text_list)
    details["req_credits"] = req_credits

    return details

def parse_thai_date_to_datetime(date_str):
    try:
        clean_str = re.sub(r"(ถึง|-|–)", " ", date_str).split()
        month_idx = -1; year = 0; day = 1
        for i, word in enumerate(clean_str):
            if word in THAI_MONTHS:
                month_idx = (THAI_MONTHS.index(word) % 12) + 1 
                if i > 0 and clean_str[i-1].isdigit(): day = int(clean_str[i-1])
            elif word.isdigit() and int(word) > 2400: year = int(word) - 543
        if month_idx > 0 and year > 0: return datetime(year, month_idx, day)
    except: pass
    return None

def get_round_priority(course_info):
    now = datetime.now()
    dt = parse_thai_date_to_datetime(course_info.get('date_range', ''))
    if dt:
        if (now - dt).days > 60: return 4 # Closed
        elif now < dt: return 2 # Future
        else: return 1 # Open
    return 3 # Unknown

def detect_intent(question):
    q = question.lower()
    if any(x in q for x in ["วันไหน", "เมื่อไหร่", "ตอนไหน", "ช่วงไหน"]): return "check_date"
    if any(x in q for x in ["เกรด", "gpax", "คะแนน", "หน่วยกิต", "คณิต", "วิทย์", "อังกฤษ", "ยื่น", "สาขาไหน", "เข้าอะไร", "สมัคร"]): return "check_eligibility"
    return "general_info"

# =====================================================
# MAIN LOGIC
# =====================================================
def ask_balanced(question: str, history: list = None, student_data: dict = None) -> str:
    db = load_vector_db()
    if not db: return "⚠️ ระบบกำลังปรับปรุงข้อมูล..."
    
    # 1. Prepare Data (ส่ง student_data จาก OCR เข้าไป)
    profile = get_student_profile(history, ocr_data=student_data)
    
    intent = detect_intent(question)
    docs = db.similarity_search(question, k=35)
    
    courses = []
    seen = set()
    for d in docs:
        info = extract_course_details(d.page_content)
        if info:
            key = f"{info['major']}_{info['round']}"
            if key not in seen:
                courses.append(info)
                seen.add(key)

    target_round = None
    q_lower = question.lower()
    if "port" in q_lower: target_round = "Portfolio"
    elif "quota" in q_lower or "โควต้า" in q_lower: target_round = "Quota"
    elif "admission" in q_lower: target_round = "Admission"

    # -------------------------------------------------
    # BUILD RESPONSE
    # -------------------------------------------------
    if (intent in ["check_eligibility", "check_date"] or target_round) and courses:
        
        # --- PART 1: SHOW FULL STUDENT PROFILE (HEADER) ---
        response = f"👤 **ข้อมูลของคุณ:** {profile['name']}\n"
        
        # แสดง GPAX และ เกรดรายวิชา (ถ้ามี)
        grades_display = [f"⭐ GPAX: {profile['gpax']}"]
        if profile['math_gpa'] > 0: grades_display.append(f"🧮 คณิต: {profile['math_gpa']}")
        if profile['sci_gpa'] > 0:  grades_display.append(f"🧪 วิทย์: {profile['sci_gpa']}")
        if profile['eng_gpa'] > 0:  grades_display.append(f"🇬🇧 Eng: {profile['eng_gpa']}")
        
        response += f"> {' | '.join(grades_display)}\n"
        
        # แสดงหน่วยกิตที่มี
        credits_display = []
        if profile['math_credit'] > 0: credits_display.append(f"คณิต {int(profile['math_credit'])} นก.")
        if profile['sci_credit'] > 0:  credits_display.append(f"วิทย์ {int(profile['sci_credit'])} นก.")
        if profile['eng_credit'] > 0:  credits_display.append(f"Eng {int(profile['eng_credit'])} นก.")
        
        if credits_display:
            response += f"> 📚 **หน่วยกิต:** {' | '.join(credits_display)}\n"
        else:
            response += "> 📚 **หน่วยกิต:** (ไม่พบข้อมูลหน่วยกิต)\n"
            
        response += "\n" + ("-" * 30) + "\n\n"

        # --- PART 2: COMPARE & FILTER ---
        eligible_courses = []
        
        for c in courses:
            if target_round and target_round not in c['round']: continue
            if profile["gpax"] > 0 and profile["gpax"] < c["min_gpax"]: continue
            
            c['priority'] = get_round_priority(c)
            eligible_courses.append(c)
        
        if not target_round and eligible_courses:
            eligible_courses.sort(key=lambda x: x['priority'])
            best_priority = eligible_courses[0]['priority']
            eligible_courses = [c for c in eligible_courses if c['priority'] <= best_priority]

        eligible_courses.sort(key=lambda x: x['major'])

        if eligible_courses:
            display_round = eligible_courses[0]['round']
            status_text = {1: "🟢 เปิดรับสมัครอยู่", 2: "🟡 เร็วๆ นี้", 3: "⚪ ข้อมูลทั่วไป", 4: "🔴 ปิดรับแล้ว"}.get(eligible_courses[0]['priority'], "")
            
            response += f"🎯 **ผลการตรวจสอบสิทธิ์: รอบ {display_round}** ({status_text})\n"
            response += "พี่เทียบเกณฑ์ให้แล้วตามรายการนี้ครับ:\n\n"

            # --- PART 3: CARD DISPLAY ---
            for c in eligible_courses:
                warning_list = []
                
                # 1. Check Credits
                req_c = c['req_credits']
                if req_c['math'] > 0:
                    if profile['math_credit'] == 0:
                        warning_list.append(f"❓ เช็คหน่วยกิตคณิต (ใช้ {req_c['math']})")
                    elif profile['math_credit'] < req_c['math']:
                        warning_list.append(f"⚠️ คณิตขาด {req_c['math'] - profile['math_credit']}")
                
                if req_c['sci'] > 0:
                    if profile['sci_credit'] == 0:
                        warning_list.append(f"❓ เช็คหน่วยกิตวิทย์ (ใช้ {req_c['sci']})")
                    elif profile['sci_credit'] < req_c['sci']:
                        warning_list.append(f"⚠️ วิทย์ขาด {req_c['sci'] - profile['sci_credit']}")

                # 2. Check Grades
                if c['min_math'] > 0:
                    if profile['math_gpa'] == 0:
                         warning_list.append(f"❓ เช็คเกรดคณิต (ใช้ {c['min_math']})")
                    elif profile['math_gpa'] < c['min_math']:
                        warning_list.append(f"⚠️ เกรดคณิตไม่ถึง ({c['min_math']})")

                if c['min_eng'] > 0:
                    if profile['eng_gpa'] == 0:
                         warning_list.append(f"❓ เช็คเกรด Eng (ใช้ {c['min_eng']})")
                    elif profile['eng_gpa'] < c['min_eng']:
                        warning_list.append(f"⚠️ เกรด Eng ไม่ถึง ({c['min_eng']})")

                # Display Requirements
                req_txt_list = []
                if c['min_math'] > 0: req_txt_list.append(f"เกรดคณิต {c['min_math']}")
                if c['min_eng'] > 0: req_txt_list.append(f"เกรด Eng {c['min_eng']}")
                
                credit_req_text = req_c['text'].replace("นก.", "หน่วยกิต") if req_c['text'] != "-" else ""
                if credit_req_text: req_txt_list.append(f"{credit_req_text}")
                
                req_display = " | ".join(req_txt_list) if req_txt_list else "ไม่กำหนดเพิ่ม"

                # Card Output
                response += f"> 🎓 **{c['major']}**\n"
                
                if not warning_list:
                    response += f"> ✅ **สถานะ:** ผ่านเกณฑ์เบื้องต้น\n"
                else:
                    response += f"> 🚨 **เตือน:** {' | '.join(warning_list)}\n"
                
                response += f"> 📝 **เกณฑ์:** GPAX {c['min_gpax']} ({req_display})\n"
                response += f"> 📅 **รับสมัคร:** {c['date_range']}\n"
                response += "\n"
            
            return response.strip()
        else:
            return f"❌ จากข้อมูลของคุณ ({profile['gpax']}) ยังไม่พบสาขาที่เปิดรับในรอบนี้ หรือเกรดอาจจะไม่ถึงเกณฑ์ครับ"

    llm = get_llm()
    try: return llm.invoke(f"Context: ... Question: {question}").strip()
    except: return "ระบบขัดข้อง"