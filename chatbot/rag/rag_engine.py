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

ROUND_ORDER_MAP = {"Portfolio": 1,"MOU": 1.2, "Quota": 2, "Admission": 3, "Direct Admission": 4}
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
    try:
        if not value: return 0.0
        clean_val = str(value).replace(",", "").strip()
        match = re.search(r"(\d+(\.\d+)?)", clean_val)
        if match:
            return float(match.group(1))
        return 0.0
    except (ValueError, TypeError):
        return 0.0

def get_student_profile(history, ocr_data=None):
    profile = {
        "name": "น้อง", 
        "gpax": 0.0, 
        "math_gpa": 0.0, "sci_gpa": 0.0, "eng_gpa": 0.0,
        "math_credit": 0.0, "sci_credit": 0.0, "eng_credit": 0.0
    }

    if ocr_data and isinstance(ocr_data, dict):
        profile["name"] = ocr_data.get("name", "น้อง")
        profile["gpax"] = safe_float(ocr_data.get("gpax"))
        profile["math_gpa"] = safe_float(ocr_data.get("math_gpa"))
        profile["sci_gpa"]  = safe_float(ocr_data.get("science_gpa")) 
        profile["eng_gpa"]  = safe_float(ocr_data.get("english_gpa")) 
        profile["math_credit"] = safe_float(ocr_data.get("math_credit"))
        profile["sci_credit"]  = safe_float(ocr_data.get("science_credit"))
        profile["eng_credit"]  = safe_float(ocr_data.get("english_credit"))
        return profile 

    if history:
        for msg in reversed(history):
            content = msg.get("content", "")
            if any(x in content for x in ["[DATA_START]", "ข้อมูล", "Profile", "Name", "ชื่อ", "GPA"]):
                
                if profile["name"] == "น้อง":
                    name_match = re.search(r"(?:ชื่อ|Name)[:\s]*([^\s\n]+)", content, re.IGNORECASE)
                    if name_match: profile["name"] = name_match.group(1)
                
                if profile["gpax"] == 0:
                    gpax_match = re.search(r"(?:GPAX|เกรดเฉลี่ย|GPA)[^0-9]*?([\d]\.[\d]{1,2})", content, re.IGNORECASE)
                    if gpax_match: profile["gpax"] = float(gpax_match.group(1))

                if profile["math_credit"] == 0:
                    m_c = re.search(r"(?:หน่วยกิต|Credit|นก\.|Unit)[^0-9\n]*(?:คณิต|Math)[^0-9\n]*[:\s]*(\d+)", content, re.IGNORECASE)
                    if m_c: profile["math_credit"] = float(m_c.group(1))
                if profile["sci_credit"] == 0:
                    s_c = re.search(r"(?:หน่วยกิต|Credit|นก\.|Unit)[^0-9\n]*(?:วิทย์|Sci)[^0-9\n]*[:\s]*(\d+)", content, re.IGNORECASE)
                    if s_c: profile["sci_credit"] = float(s_c.group(1))
                if profile["eng_credit"] == 0:
                    e_c = re.search(r"(?:หน่วยกิต|Credit|นก\.|Unit)[^0-9\n]*(?:อังกฤษ|Eng|Foreign)[^0-9\n]*[:\s]*(\d+)", content, re.IGNORECASE)
                    if e_c: profile["eng_credit"] = float(e_c.group(1))

                if profile["math_gpa"] == 0:
                    m_g = re.search(r"(?:เกรด|GPA|Grade)[^0-9\n]*(?:คณิต|Math)[^0-9\n]*[:\s]*([0-4]\.?\d*)", content, re.IGNORECASE)
                    if m_g: profile["math_gpa"] = float(m_g.group(1))
                if profile["sci_gpa"] == 0:
                    s_g = re.search(r"(?:เกรด|GPA|Grade)[^0-9\n]*(?:วิทย์|Sci)[^0-9\n]*[:\s]*([0-4]\.?\d*)", content, re.IGNORECASE)
                    if s_g: profile["sci_gpa"] = float(s_g.group(1))
                if profile["eng_gpa"] == 0:
                    e_g = re.search(r"(?:เกรด|GPA|Grade)[^0-9\n]*(?:อังกฤษ|Eng|Foreign)[^0-9\n]*[:\s]*([0-4]\.?\d*)", content, re.IGNORECASE)
                    if e_g: profile["eng_gpa"] = float(e_g.group(1))
                
                if profile["gpax"] > 0 and profile["math_credit"] > 0:
                    break
    return profile

def extract_course_details(text):
    details = {}
    
    found_round = False
    for r_key in ROUND_ORDER_MAP.keys():
        if r_key in text:
            details["round"] = r_key
            found_round = True
            break
    if not found_round: 
        if "รอบที่ 1" in text or "พอร์ต" in text: details["round"] = "Portfolio"
        elif "รอบที่ 1.2" in text or "MOU" in text: details["round"] = "MOU"
        elif "รอบที่ 2" in text or "โควตา" in text: details["round"] = "Quota"
        elif "รอบที่ 3" in text or "แอดมิชชั่น" in text: details["round"] = "Admission"
        elif "รอบที่ 4" in text or "ไดเรกแอดมิชชั่น" in text: details["round"] = "Direct Admission"
        else: details["round"] = "General"

    # ★ แก้ไข: ดึงจาก "สาขาวิชา" ก่อน เพื่อเอาชื่อเต็มที่มีขีดต่อท้าย หากไม่มีค่อยหาคำว่า "หลักสูตร" ★
    major_match = re.search(r"สาขาวิชา:\s*(.+)", text)
    if not major_match:
        major_match = re.search(r"หลักสูตร:\s*(.+)", text)
        
    if major_match: details["major"] = major_match.group(1).strip()
    else: return None 

    gpax_match = re.search(r"GPAX ขั้นต่ำ:\s*([\d\.]+)", text)
    details["min_gpax"] = float(gpax_match.group(1)) if gpax_match else 0.0

    seat_match = re.search(r"จำนวนรับ:\s*(\d+)", text)
    details["seats"] = int(seat_match.group(1)) if seat_match else 0

    math_match = re.search(r"(?:เกรด|GPA|ผลการเรียน).*?คณิต.*?(?:ไม่ต่ำกว่า|ขั้นต่ำ|:|>=)\s*([\d\.]+)", text)
    details["min_math"] = float(math_match.group(1)) if math_match else 0.0

    sci_match = re.search(r"(?:เกรด|GPA|ผลการเรียน).*?วิทย.*?(?:ไม่ต่ำกว่า|ขั้นต่ำ|:|>=)\s*([\d\.]+)", text)
    details["min_sci"] = float(sci_match.group(1)) if sci_match else 0.0

    eng_match = re.search(r"(?:เกรด|GPA|ผลการเรียน).*?(?:อังกฤษ|ภาษาต่างประเทศ|Eng).*?(?:ไม่ต่ำกว่า|ขั้นต่ำ|:|>=)\s*([\d\.]+)", text)
    details["min_eng"] = float(eng_match.group(1)) if eng_match else 0.0

    url_match = re.search(r"(https?://[^\s]+)", text)
    details["website"] = url_match.group(1) if url_match else "-"

    date_range = "-"
    range_match = re.search(r"ช่วงเวลาการรับสมัคร[:\s]*(.+)", text)
    if range_match:
        raw_date = range_match.group(1).strip()
        if re.search(r"\d{4}", raw_date): date_range = raw_date
    
    if date_range == "-":
        fallback_match = re.search(r"(?:รับสมัคร|วันที่)[:\s]*([0-9]{1,2}.*?[0-9]{4}.*?[0-9]{4})", text)
        if fallback_match: date_range = fallback_match.group(1).strip()
    
    details["date_range"] = date_range

    iv_match = re.search(r"กำหนดการสัมภาษณ์:\s*-\s*วันที่:\s*([^\n]+)", text)
    if iv_match:
        details["interview_date"] = iv_match.group(1).strip()
    else:
        details["interview_date"] = "-"

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

    details["full_text"] = text
    return details

# =====================================================
# FIXED DATE PARSER
# =====================================================
def parse_thai_date_to_datetime(date_str):
    try:
        clean_str = re.sub(r"(ถึง|-|–|to)", " ", date_str).split()
        month_idx = -1
        year = 0
        day = 1
        
        for i, word in enumerate(clean_str):
            if word in THAI_MONTHS:
                month_idx = (THAI_MONTHS.index(word) % 12) + 1
                if i > 0 and clean_str[i-1].isdigit():
                    day = int(clean_str[i-1])
            elif word.isdigit() and int(word) > 2400:
                year = int(word) - 543 
                if month_idx != -1: return datetime(year, month_idx, day)

        if month_idx > 0 and year > 0: return datetime(year, month_idx, day)
    except: pass
    return None

def get_round_priority(course_info):
    now = datetime.now()
    dt = parse_thai_date_to_datetime(course_info.get('date_range', ''))
    if dt:
        if (now - dt).days > 60: return 4 
        elif now < dt: return 2 
        else: return 1 
    return 3

def detect_intent(question):
    q = question.lower()
    
    if any(x in q for x in ["ไม่พอ", "ไม่ถึง", "เข้าไม่ได้", "ไม่ได้"]):
        return "check_failed"

    if any(x in q for x in ["มีสาขา", "กี่สาขา", "สาขาอะไรบ้าง", "สาขาไหนบ้าง", "รายชื่อสาขา", "เปิดรับสาขา"]):
        if not any(y in q for y in ["เข้า", "ยื่น", "ฉัน", "ผม", "หนู", "เกรด", "gpax", "คะแนน", "ติดไหม"]):
            return "list_all_majors"

    if any(x in q for x in ["วันไหน", "เมื่อไหร่", "ตอนไหน", "ช่วงไหน"]): 
        return "check_date"
        
    if any(x in q for x in ["เกรด", "gpax", "คะแนน", "หน่วยกิต", "คณิต", "วิทย์", "อังกฤษ", "ยื่น", "สาขาไหน", "เข้าอะไร", "ผ่านไหม", "เกณฑ์", "พอที่จะสมัคร", "อนุโลม", "ข้อยกเว้น", "ขาด", "โอกาส", "ติดไหม", "สัมภาษณ์ติด", "ยื่นที่อื่น"]): 
        return "check_eligibility"
        
    if any(x in q for x in ["เว็บ", "ลิงก์", "link", "ที่ไหน", "รายละเอียดเพิ่มเติม", "สมัครยังไง"]): 
        return "general_info"
        
    return "general_info"

# =====================================================
# MAIN LOGIC
# =====================================================
def ask_balanced(question: str, history: list = None, student_data: dict = None) -> str:
    db = load_vector_db()
    if not db: return "⚠️ ระบบกำลังเตรียมข้อมูล สักครู่นะครับ..."
    
    profile = get_student_profile(history, ocr_data=student_data)
    intent = detect_intent(question)
    docs = db.similarity_search(question, k=40)
    
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
    if any(x in q_lower for x in ["port", "รอบ 1", "รอบ1", "รอบที่ 1"]): 
        target_round = "Portfolio"
    elif any(x in q_lower for x in ["mou", "รอบ 1.2", "รอบ1.2", "รอบที่ 1.2","เอ็มโอยู","เอ็ม.โอ.ยู", "เอ็ม โอยู"]):
        target_round = "MOU"
    elif any(x in q_lower for x in ["quota", "โควตา", "รอบ 2", "รอบ2", "รอบที่ 2"]): 
        target_round = "Quota"
    elif any(x in q_lower for x in ["admission", "แอดมิชชั่น", "แอดมิชชัน", "รอบ 3", "รอบ3", "รอบที่ 3"]): 
        target_round = "Admission"
    elif any(x in q_lower for x in ["direct admission", "ไดเรกแอดมิชชั่น", "ไดเรกแอดมิชชัน", "รอบ 4", "รอบ4", "รอบที่ 4"]): 
        target_round = "Direct Admission"

    # ★ ปรับปรุงการค้นหาสาขาให้รองรับชื่อที่มีขีด (-) หรือวงเล็บ ★
    target_majors = []
    q_norm = q_lower.replace("สาขาวิชา", "").replace("วิทยาศาสตรบัณฑิต", "").replace("การ", "").replace("ความ", "").replace("และ", "").replace(" ", "")
    
    for c in courses:
        # ตัดส่วนขยายหลังเครื่องหมาย - หรือ ( ออก เพื่อใช้เทียบคำศัพท์หลักกับที่ผู้ใช้พิมพ์
        base_major = re.split(r'[-–(]', c['major'])[0]
        major_norm = base_major.lower().replace("สาขาวิชา", "").replace("วิทยาศาสตรบัณฑิต", "").replace("การ", "").replace("ความ", "").replace("และ", "").replace(" ", "")
        
        if len(major_norm) > 3 and major_norm in q_norm:
            target_majors.append(c['major'])

    if not target_majors and any(x in q_lower for x in ["คณะ", "สาขา"]):
        general_kw = ["ไหน", "อะไร", "กี่", "ทั้งหมด", "ใด"]
        is_general_question = any(kw in q_lower for kw in general_kw)
        
        if not is_general_question:
            return "❌ **ขออภัยครับ ระบบไม่มีข้อมูลของคณะหรือสาขาวิชาที่คุณสอบถามครับ**\n<br><br>*(หมายเหตุ: บอทสามารถให้ข้อมูลได้เฉพาะสาขาวิชาที่มีอยู่ในเอกสารประกาศรับสมัครเท่านั้น โปรดตรวจสอบชื่อสาขาวิชาอีกครั้งครับ)*"

    # ==========================================
    # โหมดที่ 1: แสดง "รายชื่อสาขาทั้งหมด" (ไม่ได้เช็คเกรด)
    # ==========================================
    if intent == "list_all_majors" and courses:
        target_courses = []
        for c in courses:
            if target_round and target_round not in c['round']: continue
            target_courses.append(c)
            
        if not target_courses:
            target_courses = courses 
            
        unique_courses = []
        seen_majors = set()
        for c in target_courses:
            k = f"{c['major']}_{c['round']}"
            if k not in seen_majors:
                unique_courses.append(c)
                seen_majors.add(k)
        unique_courses.sort(key=lambda x: x['major'])
        
        response = f"📋 **รายชื่อสาขาที่เปิดรับสมัคร"
        response += f" ในรอบ {target_round}" if target_round else ""
        response += f" มีทั้งหมด {len(unique_courses)} สาขา ดังนี้ครับ:**<br><br>"
        
        for idx, c in enumerate(unique_courses, 1):
            response += f"🔹 {idx}. {c['major']}\n"
            
        return response.strip()

    # ==========================================
    # โหมดที่ 2: หา "สาขาที่ไม่ผ่านเกณฑ์" (check_failed)
    # ==========================================
    if intent == "check_failed" and courses:
        failed_courses = []
        passed_courses_for_recommend = [] 
        
        if not target_round:
            courses.sort(key=lambda x: (get_round_priority(x), ROUND_ORDER_MAP.get(x['round'], 99)))
            target_round = courses[0]['round'] if courses else None

        for c in courses:
            if target_round and target_round not in c['round']: continue
            
            warning_list = []
            req_c = c['req_credits']
            
            if profile["gpax"] > 0 and profile["gpax"] < c["min_gpax"]:
                warning_list.append(f"⚠️ GPAX ไม่ถึง (มี {profile['gpax']}, ต้องการ {c['min_gpax']})")

            if req_c['math'] > 0 and profile['math_credit'] < req_c['math']: 
                warning_list.append(f"⚠️ ขาดหน่วยกิตคณิต (มี {profile['math_credit']}/{req_c['math']})")
            if req_c['sci'] > 0 and profile['sci_credit'] < req_c['sci']: 
                warning_list.append(f"⚠️ ขาดหน่วยกิตวิทย์ (มี {profile['sci_credit']}/{req_c['sci']})")
            if c['min_math'] > 0 and profile['math_gpa'] < c['min_math']: 
                warning_list.append(f"⚠️ เกรดคณิตไม่ถึง (มี {profile['math_gpa']}, ต้องการ {c['min_math']})")
            if c['min_eng'] > 0 and profile['eng_gpa'] < c['min_eng']: 
                warning_list.append(f"⚠️ เกรด Eng ไม่ถึง (มี {profile['eng_gpa']}, ต้องการ {c['min_eng']})")

            if warning_list: 
                # ★ เปลี่ยนตัวกรองจาก target_major (string) เป็น target_majors (list) ★
                if target_majors and c['major'] not in target_majors: continue 
                c['warning_list'] = warning_list
                failed_courses.append(c)
            else:
                passed_courses_for_recommend.append(c['major'])

        if failed_courses:
            response = f"📋 **สรุปสาขาที่คุณยังไม่ผ่านเกณฑ์เบื้องต้น ในรอบ {target_round}**:\n\n"
            for c in failed_courses:
                response += f"> 🎓 **{c['major']}**\n"
                response += f"> 🚨 **สาเหตุ:** {' | '.join(c['warning_list'])}\n\n"
            
            try:
                llm = get_llm()
                passed_list = list(set(passed_courses_for_recommend))
                passed_str = ", ".join(passed_list[:4]) if passed_list else ""
                
                if passed_str:
                    combo_prompt = f"""ในฐานะรุ่นพี่แนะแนว (ตอบเป็นเพศชาย ลงท้ายด้วยครับ ห้ามใช้คำว่า 'ค่ะ' เด็ดขาด)
นักเรียนถามว่า: "{question}"
สาขาอื่นที่นักเรียนผ่านเกณฑ์และสามารถยื่นได้คือ: {passed_str}

คำสั่ง: แนะนำสาขาที่ผ่านเกณฑ์ให้นักเรียนลองพิจารณายื่นแทนสั้นๆ 1 บรรทัด อย่างเป็นธรรมชาติ ห้ามบอกว่าไม่มีข้อมูลเด็ดขาด
คำตอบ:"""
                else:
                    combo_prompt = f"""ในฐานะรุ่นพี่แนะแนว (ตอบเป็นเพศชาย ลงท้ายด้วยครับ ห้ามใช้คำว่า 'ค่ะ' เด็ดขาด)
นักเรียนถามว่า: "{question}"

คำสั่ง: ให้กำลังใจนักเรียนสั้นๆ 1 บรรทัด และแนะนำให้ลองรอดูเกณฑ์รอบอื่นๆ เนื่องจากรอบนี้ยังไม่มีสาขาที่ตรงตามเกณฑ์
คำตอบ:"""
                    
                addon_answer = llm.invoke(combo_prompt).strip()
                addon_answer = re.sub(r"^(คำตอบ:|พี่ Gaku:)\s*", "", addon_answer).strip()
                if addon_answer and len(addon_answer) > 5:
                    response += f"<br><br>💡 **พี่ Gaku แนะนำทางเลือกเพิ่มเติม:**\n{addon_answer}\n"
            except Exception as e:
                logger.error(f"Combo LLM Error: {e}")
                
            return response.strip()
        else:
            return f"🎉 ยินดีด้วยครับ! จากข้อมูลของคุณ ดูเหมือนจะผ่านเกณฑ์เบื้องต้นของทุกสาขาในรอบ {target_round} เลยครับ"

    # ==========================================
    # โหมดที่ 3: หา "สาขาที่ผ่านเกณฑ์" (check_eligibility)
    # ==========================================
    if intent == "check_eligibility" and courses:
        eligible_courses = []
        for c in courses:
            if target_round and target_round not in c['round']: continue
            # ★ เปลี่ยนตัวกรองเป็น array ★
            if target_majors and c['major'] not in target_majors: continue 
            if profile["gpax"] > 0 and profile["gpax"] < c["min_gpax"]: continue
            
            c['priority'] = get_round_priority(c)
            eligible_courses.append(c)
        
        if not target_round and eligible_courses:
            eligible_courses.sort(key=lambda x: (x['priority'], ROUND_ORDER_MAP.get(x['round'], 99)))
            best_round = eligible_courses[0]['round']
            eligible_courses = [c for c in eligible_courses if c['round'] == best_round]

        eligible_courses.sort(key=lambda x: x['major'])

        if eligible_courses:
            display_round = eligible_courses[0]['round']
            status_text = {1: "🟢 เปิดรับสมัครอยู่", 2: "🟡 เร็วๆ นี้", 3: "⚪ ข้อมูลทั่วไป", 4: "🔴 ปิดรับแล้ว"}.get(eligible_courses[0]['priority'], "")
            
            response = f"👤 **ข้อมูลของคุณ:** {profile['name']}\n\n"
            response += f"⭐ **GPAX (เกรดเฉลี่ยรวม):** {profile['gpax']}\n\n"
            
            m_g = str(profile['math_gpa']) if profile['math_gpa'] > 0 else "-"
            s_g = str(profile['sci_gpa'])  if profile['sci_gpa'] > 0  else "-"
            e_g = str(profile['eng_gpa'])  if profile['eng_gpa'] > 0  else "-"
            
            m_c = f"{int(profile['math_credit'])}" if profile['math_credit'] > 0 else "-"
            s_c = f"{int(profile['sci_credit'])}"  if profile['sci_credit'] > 0  else "-"
            e_c = f"{int(profile['eng_credit'])}"  if profile['eng_credit'] > 0  else "-"
            
            response += f"📊 **เกรดรายวิชา:**\n"
            response += f"| คณิตศาสตร์: {m_g}\n"
            response += f"| วิทยาศาสตร์: {s_g}\n"
            response += f"| ภาษาอังกฤษ: {e_g}\n\n"
            
            response += f"📚 **หน่วยกิต:**\n"
            response += f"| คณิตศาสตร์: {m_c} หน่วยกิต\n"
            response += f"| วิทยาศาสตร์: {s_c} หน่วยกิต\n"
            response += f"| ภาษาอังกฤษ: {e_c} หน่วยกิต\n\n"
            
            response += "<br><br>"

            response += f"🎯 **ผลการตรวจสอบสิทธิ์: รอบ {display_round}** ({status_text})\n"
            response += "พี่คัดเลือกสาขามาให้ตามเกณฑ์ครับ:\n\n"

            passed_courses_count = 0 

            for c in eligible_courses:
                warning_list = []
                req_c = c['req_credits']
                
                if req_c['math'] > 0 and profile['math_credit'] < req_c['math']: 
                    warning_list.append(f"⚠️ ขาดหน่วยกิตคณิต (มี {profile['math_credit']}/{req_c['math']})")
                if req_c['sci'] > 0 and profile['sci_credit'] < req_c['sci']: 
                    warning_list.append(f"⚠️ ขาดหน่วยกิตวิทย์ (มี {profile['sci_credit']}/{req_c['sci']})")
                if c['min_math'] > 0 and profile['math_gpa'] < c['min_math']: 
                    warning_list.append(f"⚠️ เกรดคณิตไม่ถึง (มี {profile['math_gpa']}, ต้องการ {c['min_math']})")
                if c['min_eng'] > 0 and profile['eng_gpa'] < c['min_eng']: 
                    warning_list.append(f"⚠️ เกรด Eng ไม่ถึง (มี {profile['eng_gpa']}, ต้องการ {c['min_eng']})")

                c['warning_list'] = warning_list

                # ★ เปลี่ยนตัวกรองเป็น array ★
                if warning_list and not target_majors:
                    continue

                passed_courses_count += 1

                req_txt_list = []
                if c['min_math'] > 0: req_txt_list.append(f"เกรดคณิต {c['min_math']}")
                if c['min_eng'] > 0: req_txt_list.append(f"เกรด Eng {c['min_eng']}")
                credit_req_text = req_c['text'].replace("นก.", "หน่วยกิต") if req_c['text'] != "-" else ""
                if credit_req_text: req_txt_list.append(f"{credit_req_text}")
                req_display = " | ".join(req_txt_list) if req_txt_list else "ไม่กำหนดเพิ่มเติม"

                response += f"> 🎓 **{c['major']}**\n"
                if not warning_list:
                    response += f"> ✅ **สถานะ:** ผ่านเกณฑ์เบื้องต้น\n"
                else:
                    response += f"> 🚨 **เตือน:** {' | '.join(warning_list)}\n"
                
                response += f"> 📝 **เกณฑ์ขั้นต่ำ:** GPAX {c['min_gpax']} ({req_display})\n"
                response += f"> 📅 **รับสมัคร:** {c['date_range']}\n"
                
                if c.get('interview_date') and c['interview_date'] != "-":
                    response += f"> 🗣️ **สอบสัมภาษณ์:** {c['interview_date']}\n"

                if c['website'] != "-":
                    response += f"> 🌐 **รายละเอียดเพิ่มเติม:** {c['website']}\n"
                response += "\n"

            if passed_courses_count == 0 and not target_majors:
                 response_fail = f"❌ จากข้อมูลของคุณ (GPAX {profile['gpax']}) ยังไม่พบสาขาที่คุณสมบัติ (เกรด/หน่วยกิต) ถึงเกณฑ์ในรอบ {display_round} ครับ"
                 return response_fail

            nuance_keywords = ["ทำไม", "อย่างไร", "อนุโลม", "ข้อยกเว้น", "ได้ไหม", "พอที่", "ขาด", "แนะนำ", "เท่าไหร่", "โอกาส", "ติดไหม", "ยื่นที่อื่น"]
            if any(k in question for k in nuance_keywords) or len(question) > 30:
                try:
                    llm = get_llm()
                    first_course = eligible_courses[0]
                    warnings = first_course.get('warning_list', [])
                    
                    eval_status = "❌ ไม่ผ่านเกณฑ์ (ไม่สามารถสมัครได้)" if warnings else "✅ ผ่านเกณฑ์ขั้นต่ำ"
                    eval_reason = " ".join(warnings) if warnings else "ข้อมูลหน่วยกิตและเกรดถึงเกณฑ์ที่ระบุ"
                    
                    combo_prompt = f"""
ตอบคำถามนักเรียนสั้นๆ 1-2 บรรทัด โดยอิงจากสถานะเกณฑ์การรับสมัคร (เป็นเพศชาย ลงท้ายด้วยครับ)

คำถามนักเรียน: "{question}"
สถานะการประเมินจากระบบ: {eval_status}
รายละเอียด/เหตุผล: {eval_reason}

ข้อบังคับ:
- ถ้าระบบบอกว่า "ไม่ผ่านเกณฑ์" ให้ยืนยันไปตรงๆ ว่าสมัครไม่ได้ และบอกเหตุผล ห้ามให้ความหวัง
- มหาวิทยาลัยไม่มีนโยบายอนุโลมใดๆ ทั้งสิ้น

คำตอบ:"""
                    addon_answer = llm.invoke(combo_prompt).strip()
                    addon_answer = re.sub(r"^(คำตอบ:|พี่ Gaku:)\s*", "", addon_answer).strip()
                    if addon_answer:
                        response += f"<br><br>💡 **พี่ Gaku ขอสรุปเพิ่มเติม:**\n{addon_answer}\n"
                except Exception as e:
                    logger.error(f"Combo LLM Error: {e}")

            return response.strip()
        else:
            msg = f"❌ จากข้อมูล GPAX {profile['gpax']} ยังไม่พบสาขาที่เปิดรับ"
            # ★ อัปเดตข้อความ error ★
            if target_majors: msg += f" สำหรับสาขา **{target_majors[0]}**"
            if target_round: msg += f" ใน **รอบ {target_round}**"
            msg += " ครับ หรือเกรด/หน่วยกิตอาจจะไม่ถึงเกณฑ์"
            return msg

    # ==========================================
    # กรณี 4: ถามข้อมูลทั่วไป (ให้ LLM เรียบเรียงคำตอบแบบ Full)
    # ==========================================
    llm = get_llm()
    context_text = ""
    
    # ★ เปลี่ยนตัวกรองเป็น array ★
    filtered_courses = [c for c in courses if not target_majors or c['major'] in target_majors]
    if not filtered_courses: filtered_courses = courses

    for c in filtered_courses[:3]: 
        context_text += f"--- {c['major']} ({c['round']}) ---\n{c.get('full_text', '')}\n"

    student_context = ""
    if profile['gpax'] > 0:
        student_context = f"ข้อมูลของผู้ใช้ปัจจุบัน: ชื่อ {profile['name']}, GPAX {profile['gpax']}, มีหน่วยกิต คณิต {profile['math_credit']} / วิทย์ {profile['sci_credit']} / Eng {profile['eng_credit']}"

    prompt = f"""
    คุณคือ 'พี่ Gaku' ผู้ช่วยตอบคำถามการรับสมัครนักศึกษาของ มทร.ธัญบุรี
    จงตอบคำถามโดยอิงจาก Context ที่ให้มาเท่านั้น
    {student_context}

    คำสั่ง (ห้ามทวนคำสั่งนี้ในคำตอบ):
    - ตอบเป็นภาษาไทย เป็นธรรมชาติ และเป็นกันเอง ลงท้ายด้วย 'ครับ'
    - หากเขาถามหาสาขาใดสาขาหนึ่ง ให้ตอบเฉพาะสาขานั้น
    - ห้ามแต่งข้อมูลเองเด็ดขาด

    Context:
    {context_text}

    Question: {question}
    Answer (Thai):"""

    try: 
        answer = llm.invoke(prompt).strip()
        return answer
    except: 
        return "ขออภัยครับ ระบบขัดข้องชั่วคราว"