import pandas as pd
import os

# ==============================================================================
# 1. HELPER FUNCTIONS
# ==============================================================================

def clean_text(val):
    """ล้างข้อความให้สะอาด"""
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if s.lower() in ["nan", "none", "-", "0", "0.0", "0.00"]:
        return ""
    return s

def clean_id(val):
    """ทำความสะอาดรหัสสาขา"""
    if pd.isna(val):
        return ""
    text = str(val).strip().upper()
    if text.endswith(".0"):
        text = text[:-2]
    return text

def is_valid_score(val):
    """
    ★ สำคัญ: ตรวจสอบว่าเป็นคะแนนที่ถูกต้องหรือไม่ 
    - ต้องไม่เป็นค่าว่าง
    - ต้องสั้นกว่า 10 ตัวอักษร (กัน Text ยาวๆ หลุดมา)
    - ต้องแปลงเป็นตัวเลขได้
    """
    s = clean_text(val)
    if not s: 
        return False
    
    # ถ้าข้อความยาวเกิน 8 ตัวอักษร แสดงว่าเป็นขยะ (เช่น CSV row ที่หลุดมา)
    if len(s) > 8: 
        return False
        
    try:
        # ลองแปลงเป็น float ดู ถ้าไม่ได้แสดงว่าไม่ใช่คะแนน
        float(s)
        return True
    except ValueError:
        return False

def find_header_row(df, keywords=("program_id", "รหัส", "type", "min_")):
    """หาบรรทัด Header"""
    for i in range(min(30, len(df))):
        row_text = " ".join(df.iloc[i].astype(str)).lower()
        if any(k in row_text for k in keywords):
            return i
    return 0

def get_round_name(round_code):
    """แปลงรหัสรอบ"""
    mapping = {
        "1_2568": "รอบที่ 1 Portfolio",
        "2_2568": "รอบที่ 2 Quota",
        "3_2568": "รอบที่ 3 Admission",
        "4_2568": "รอบที่ 4 Direct Admission",
    }
    return mapping.get(str(round_code).strip(), round_code)

def get_subject_name(col_name):
    """แปลงรหัสกลุ่มสาระเป็นชื่อวิชา"""
    mapping = {
        "21": "ภาษาไทย",
        "22": "คณิตศาสตร์",
        "23": "วิทยาศาสตร์",
        "24": "สังคมศึกษา",
        "25": "สุขศึกษา",
        "26": "ศิลปะ",
        "27": "การงานอาชีพ",
        "28": "ภาษาต่างประเทศ",
        "eng": "ภาษาอังกฤษ",
        "math": "คณิตศาสตร์",
        "sci": "วิทยาศาสตร์",
        "phy": "ฟิสิกส์",
        "chem": "เคมี",
        "bio": "ชีววิทยา"
    }
    for k, v in mapping.items():
        if k in col_name.lower():
            return v
    return None # ถ้าไม่ตรงกับอะไรเลย ให้ส่งค่า None กลับไป

def interpret_education_criteria(row):
    """แปลเงื่อนไขวุฒิการศึกษา"""
    accept, reject = [], []
    def flag(val): return str(val).strip()

    if flag(row.get("only_formal")) == "1": accept.append("ม.6 (สามัญ)")
    elif flag(row.get("only_formal")) == "2": reject.append("ม.6")

    if flag(row.get("only_international")) == "1": accept.append("โรงเรียนนานาชาติ")

    if flag(row.get("only_vocational")) == "1": accept.append("ปวช.")
    elif flag(row.get("only_vocational")) == "2": reject.append("ปวช.")

    if flag(row.get("only_non_formal")) == "1": accept.append("กศน.")
    elif flag(row.get("only_non_formal")) == "2": reject.append("กศน.")

    if flag(row.get("only_ged")) == "1": accept.append("GED")
    elif flag(row.get("only_ged")) == "2": reject.append("GED")

    return accept, reject

# ==============================================================================
# 2. SMART EXCEL LOADER
# ==============================================================================

def load_file_smart(filepath, sheet_hints):
    if not os.path.exists(filepath):
        return pd.DataFrame()

    try:
        xls = pd.ExcelFile(filepath)
        sheet = next((s for s in xls.sheet_names if any(h in s for h in sheet_hints)), None)
        if not sheet: return pd.DataFrame()

        raw = pd.read_excel(xls, sheet_name=sheet, header=None, dtype=str)
        header_idx = find_header_row(raw)

        df = pd.read_excel(xls, sheet_name=sheet, header=header_idx, dtype=str)
        df.columns = df.columns.str.strip().str.lower()
        df = df.dropna(how="all")
        return df
    except:
        return pd.DataFrame()

# ==============================================================================
# 3. MAIN RAG PARSER (ฉบับแก้ไข: ดึงชื่อสาขาให้ถูกต้องตามบริบท)
# ==============================================================================

def generate_tcas_rag_data(uploaded_file_path):
    df_course = load_file_smart(uploaded_file_path, ["1.2"])
    df_criteria = load_file_smart(uploaded_file_path, ["2.1"])

    if df_course.empty or df_criteria.empty: return []

    pid_course = next((c for c in df_course.columns if "program_id" in c), None)
    pid_crit = next((c for c in df_criteria.columns if "program_id" in c), None)

    if not pid_course or not pid_crit: return []

    # Map Course Info (ข้อมูลพื้นฐานจาก Sheet 1.2)
    course_map = {}
    for _, r in df_course.iterrows():
        pid = clean_id(r[pid_course])
        if not pid: continue
        course_map[pid] = {
            "uni": clean_text(r.get("university_name_th")),
            "fac": clean_text(r.get("faculty_name_th")),
            "prog": clean_text(r.get("program_name_th")),
            "major": clean_text(r.get("major_name_th")),
        }

    results = []

    for _, row in df_criteria.iterrows():
        pid = clean_id(row[pid_crit])
        if pid not in course_map: continue

        info = course_map[pid]
        round_name = get_round_name(clean_text(row.get("type")))
        start_date = clean_text(row.get("start_date"))
        end_date = clean_text(row.get("end_date"))

        # --- ส่วนแก้ไข: Logic การเลือกชื่อสาขาให้ถูกต้อง ---
        # 1. เริ่มต้นด้วยชื่อจาก Sheet 1.2
        major_display = info["major"] if (info["major"] and info["major"] != '0') else info["prog"]
        
        # 2. พยายามดึงชื่อเจาะจงจาก Sheet 2.1 (project_name_th / major_name_th)
        spec_proj = clean_text(row.get("project_name_th"))
        spec_major = clean_text(row.get("major_name_th"))
        desc_text = clean_text(row.get("description"))

        if spec_proj and spec_proj != '0':
            major_display = spec_proj
        elif spec_major and spec_major != '0':
            major_display = spec_major
        # 3. ★ แก้ไขพิเศษ: แกะชื่อจาก Description ถ้าชื่อโครงการเป็น 0 (ตามรูป Excel ของคุณ)
        elif "สาขาวิชา" in desc_text:
            try:
                # ตัดคำว่า "หลักสูตร..." ออก เอาเฉพาะหลัง "สาขาวิชา"
                parts = desc_text.split("สาขาวิชา")[-1] 
                # ตัดส่วนท้ายที่เป็นวงเล็บออก เช่น (4 ปี)
                clean_part = parts.split("(")[0].strip()
                if len(clean_part) > 3: # เช็คว่ามีความยาวพอสมควร
                    major_display = clean_part
            except:
                pass # ถ้าแกะไม่ออก ให้ใช้ชื่อเดิม
        # -----------------------------------------------------

        lines = []

        # --- Metadata ---
        lines.append(f"มหาวิทยาลัย: {info['uni']}")
        lines.append(f"คณะ: {info['fac']}")
        lines.append(f"หลักสูตร: {info['prog']}")
        lines.append(f"สาขาวิชา: {major_display}") # ใช้ชื่อที่แกะมาใหม่
        lines.append(f"รหัสสาขา: {pid}")
        lines.append(f"รอบการรับ: {round_name}")
        
        if start_date and end_date:
            lines.append(f"ช่วงเวลารับสมัคร: {start_date} ถึง {end_date}")

        amount = clean_text(row.get("receive_student_number"))
        if is_valid_score(amount):
            lines.append(f"จำนวนรับ: {amount} คน")

        # --- Qualification ---
        acc, rej = interpret_education_criteria(row)
        if acc or rej:
            lines.append("คุณสมบัติผู้สมัคร:")
            if acc: lines.append(f"- วุฒิที่รับ: {', '.join(acc)}")
            if rej: lines.append(f"- ไม่รับ: {', '.join(rej)}")

        # --- Score Criteria ---
        gpax = clean_text(row.get("min_gpax"))
        if is_valid_score(gpax):
            lines.append(f"GPAX ขั้นต่ำ: {gpax}")

        # วนลูปหาคะแนนรายวิชา
        score_lines = []
        for col in df_criteria.columns:
            if col == 'min_gpax': continue
            val = row[col]
            if not is_valid_score(val): continue 

            subj_name = get_subject_name(col)
            if not subj_name: continue

            if "min_credit_gpa" in col:
                score_lines.append(f"- หน่วยกิตวิชา{subj_name}: ไม่น้อยกว่า {val}")
            elif "min_gpa" in col:
                score_lines.append(f"- เกรดวิชา{subj_name}: ไม่ต่ำกว่า {val}")
            elif "min_tgat" in col or "min_tpat" in col or "min_a_lv" in col:
                score_lines.append(f"- คะแนน {col.replace('min_', '').upper()}: ไม่ต่ำกว่า {val}")

        if score_lines:
            lines.extend(score_lines)
        elif not is_valid_score(gpax):
            lines.append("(ไม่มีกำหนดเกณฑ์ขั้นต่ำรายวิชา)")

        # --- Conditions ---
        desc = clean_text(row.get("description"))
        cond = clean_text(row.get("condition"))
        if desc or cond:
            lines.append("เงื่อนไขเพิ่มเติม:")
            if desc and len(desc) < 500: lines.append(f"- {desc}")
            if cond and len(cond) < 500: lines.append(f"- {cond}")

        # --- Interview ---
        i_date = clean_text(row.get("interview_date"))
        i_time = clean_text(row.get("interview_time"))
        link = clean_text(row.get("link"))

        if i_date or i_time or link:
            lines.append("กำหนดการสัมภาษณ์:")
            if i_date: lines.append(f"- วันที่: {i_date}")
            if i_time: lines.append(f"- เวลา: {i_time}")
            if link: lines.append(f"- รายละเอียด: {link}")

        results.append({
            "id": pid,
            "round": round_name,
            "major_name": major_display, # ส่งชื่อที่ถูกต้องออกไปแสดงผล
            "start_date": start_date,
            "end_date": end_date,
            "header": f"{major_display} ({pid})",
            "content": "\n".join(lines),
        })

    return results