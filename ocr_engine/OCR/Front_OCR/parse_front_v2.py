# OCR/Front_OCR/parse_front_v2.py
import re
from copy import deepcopy
from typing import Any, Dict, List

FRONT_SCHEMA = {
    "document_info": {"ประเภทเอกสาร": "", "ปพ": "", "ชุดที่": "", "เลขที่": ""},
    "school_info": {
        "โรงเรียน": "", "สังกัด": "", "ตำบล/แขวง": "", "อำเภอ/เขต": "", "จังหวัด": "",
        "สำนักงานเขตพื้นที่การศึกษา": "", "วันเข้าเรียน": "", "โรงเรียนเดิม": "",
        "จังหวัดโรงเรียนเดิม": "", "ชั้นเรียนสุดท้าย": ""
    },
    "student_info": {
        "ชื่อ": "", "ชื่อสกุล": "", "เลขประจำตัวนักเรียน": "", "เลขประจำตัวประชาชน": "",
        "เกิดวันที่": "", "เพศ": "", "สัญชาติ": "", "เชื้อชาติ": "",
        "ชื่อบิดา": "", "ชื่อมารดา": ""
    }
}

ALIASES = {
    "ชุดที่": ["ชุดที่"],
    "เลขที่": ["เลขที่"],

    "โรงเรียนเดิม": ["โรงเรียนเดิม"],
    "โรงเรียน": ["โรงเรียน"],
    "สังกัด": ["สังกัด"],
    "ตำบล/แขวง": ["ตำบล/แขวง"],
    "อำเภอ/เขต": ["อำเภอ/เขต"],
    "จังหวัด": ["จังหวัด"],
    "สำนักงานเขตพื้นที่การศึกษา": ["สำนักงานเขตพื้นที่การศึกษา", "เขตพื้นที่การศึกษา"],
    "วันเข้าเรียน": ["วันเข้าเรียน", "วันที่เข้าเรียน"],
    "ชั้นเรียนสุดท้าย": ["ชั้นเรียนสุดท้าย"],

    "ชื่อ": ["ชื่อ"],
    "ชื่อสกุล": ["ชื่อสกุล"],
    "เลขประจำตัวนักเรียน": ["เลขประจำตัวนักเรียน"],
    "เลขประจำตัวประชาชน": ["เลขประจำตัวประชาชน"],
    "เกิดวันที่": ["เกิดวันที่", "วันเกิด"],
    "เพศ": ["เพศ"],
    "สัญชาติ": ["สัญชาติ"],
    "เชื้อชาติ": ["เชื้อชาติ"],
    "ชื่อบิดา": ["ชื่อ-ชื่อสกุลบิดา", "ชื่อ - ชื่อสกุลบิดา", "ชื่อสกุลบิดา", "ชื่อบิดา"],
    "ชื่อมารดา": ["ชื่อ-ชื่อสกุลมารดา", "ชื่อ - ชื่อสกุลมารดา", "ชื่อสกุลมารดา", "ชื่อมารดา"],
}

def _cleanup(v: str) -> str:
    if not v:
        return ""
    s = v.replace("\n", " ").strip()
    s = re.sub(r"\bชื่อ\s*-\s*$", "", s)  # ตัดเศษท้าย
    s = re.sub(r"\s+", " ", s)
    return s

def _split_line_by_labels(line: str, all_labels: List[str]) -> List[str]:
    line = line.strip()
    if not line:
        return []
    hits: List[int] = []
    for lb in all_labels:
        pos = line.find(" " + lb)
        if pos > 0:
            hits.append(pos + 1)
    if not hits:
        return [line]
    hits = sorted(set(hits))
    parts: List[str] = []
    start = 0
    for cut in hits:
        parts.append(line[start:cut].strip())
        start = cut
    parts.append(line[start:].strip())
    return [p for p in parts if p]

def normalize_raw_input_text(text: str) -> str:
    """
    Normalize input before parsing:
    - แปลง \\n -> \n
    - ตัด wrapper แบบ {"document_info" ... } ที่ OCR/LLM ชอบพ่นมา
    - ลบปีกกา/quote ที่หลงเหลือ
    """

    if not text:
        return ""

    s = text.strip()

    # 1) แปลง literal \\n ให้เป็น newline จริง
    s = s.replace("\\n", "\n")

    # 2) ตัด wrapper พวก {"document_info" ... (แม้จะเป็น JSON ผิดรูป)
    # ครอบคลุมทั้งแบบมี : และไม่มี :
    s = re.sub(r'^\s*\{\s*"?document_info"?\s*:?\s*', "", s, flags=re.IGNORECASE)

    # 3) ตัดปีกกา/quote ท้าย
    s = s.strip().strip('"').strip()
    s = re.sub(r"\}\s*$", "", s).strip()

    return s

def normalize_to_lines(raw_text: str) -> List[str]:
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")

    cut = text.find("ผลการเรียนรายวิชา")
    if cut != -1:
        text = text[:cut]

    text = re.sub(r":\s*", " ", text)
    text = re.sub(r"[ \t]+", " ", text)

    base_lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    all_labels = set()
    for aliases in ALIASES.values():
        for a in aliases:
            all_labels.add(a)
    all_labels.update(["ศาสนา"])  # ช่วยแยก line ที่รวมเพศ/สัญชาติ/ศาสนา
    all_labels = sorted(all_labels, key=len, reverse=True)

    final: List[str] = []
    for ln in base_lines:
        final.extend(_split_line_by_labels(ln, all_labels))
    return final

def find_value(lines: List[str], aliases: List[str]) -> str:
    for i, ln in enumerate(lines):
        for a in aliases:
            if ln == a and i + 1 < len(lines):
                return lines[i + 1].strip()
            if ln.startswith(a + " "):
                return ln[len(a):].strip()
    return ""

def find_inline(lines: List[str], label: str) -> str:
    for ln in lines:
        if ln.startswith(label + " "):
            return ln[len(label):].strip()
    return ""

def parse_front_clean_text_to_json(clean_text: str) -> Dict[str, Any]:
    clean_text = normalize_raw_input_text(clean_text)
    lines = normalize_to_lines(clean_text)
    out = deepcopy(FRONT_SCHEMA)
    joined = "\n".join(lines)

    # ประเภทเอกสาร
    doc_type = ""
    for ln in lines[:20]:
        if "ระเบียนแสดงผล" in ln:
            doc_type = ln.strip()
            break
    out["document_info"]["ประเภทเอกสาร"] = doc_type

    # ปพ/ชุดที่/เลขที่ (รองรับ ":" เพี้ยน)
    m = re.search(
    r"(ปพ\.\d)\s*(?:[: ]\s*)?([^\n]+?)\s+ชุดที่\s*(\d+)\s+เลขที่\s*(\d+)",
    joined
)
    if m:
        out["document_info"]["ปพ"] = f"{m.group(1)} : {m.group(2)}"
        out["document_info"]["ชุดที่"] = m.group(3)
        out["document_info"]["เลขที่"] = m.group(4)
    else:
        for ln in lines:
            if ln.startswith("ปพ."):
                out["document_info"]["ปพ"] = ln.strip()
                break
        out["document_info"]["ชุดที่"] = find_value(lines, ALIASES["ชุดที่"])
        out["document_info"]["เลขที่"] = find_value(lines, ALIASES["เลขที่"])

    # school_info
    out["school_info"]["โรงเรียนเดิม"] = _cleanup(find_value(lines, ALIASES["โรงเรียนเดิม"]))

    school = ""
    for i, ln in enumerate(lines):
        if ln == "โรงเรียน" and i + 1 < len(lines):
            school = lines[i + 1].strip()
            break
        if ln.startswith("โรงเรียน ") and not ln.startswith("โรงเรียนเดิม"):
            school = ln.replace("โรงเรียน", "", 1).strip()
            break
    out["school_info"]["โรงเรียน"] = _cleanup(school)

    out["school_info"]["สังกัด"] = _cleanup(find_value(lines, ALIASES["สังกัด"]))
    out["school_info"]["ตำบล/แขวง"] = _cleanup(find_value(lines, ALIASES["ตำบล/แขวง"]))
    out["school_info"]["อำเภอ/เขต"] = _cleanup(find_value(lines, ALIASES["อำเภอ/เขต"]))
    out["school_info"]["จังหวัด"] = _cleanup(find_value(lines, ALIASES["จังหวัด"]))
    out["school_info"]["สำนักงานเขตพื้นที่การศึกษา"] = _cleanup(find_value(lines, ALIASES["สำนักงานเขตพื้นที่การศึกษา"]))
    out["school_info"]["วันเข้าเรียน"] = _cleanup(find_value(lines, ALIASES["วันเข้าเรียน"]))
    out["school_info"]["ชั้นเรียนสุดท้าย"] = _cleanup(find_value(lines, ALIASES["ชั้นเรียนสุดท้าย"]))

    # จังหวัดโรงเรียนเดิม = จังหวัดหลังโรงเรียนเดิม
    prev_prov = ""
    if out["school_info"]["โรงเรียนเดิม"]:
        seen = False
        for ln in lines:
            if ln.startswith("โรงเรียนเดิม"):
                seen = True
                continue
            if seen and ln.startswith("จังหวัด"):
                prev_prov = ln.replace("จังหวัด", "", 1).strip()
                break
    out["school_info"]["จังหวัดโรงเรียนเดิม"] = _cleanup(prev_prov)

    # student_info
    out["student_info"]["ชื่อบิดา"] = _cleanup(find_value(lines, ALIASES["ชื่อบิดา"]))
    out["student_info"]["ชื่อมารดา"] = _cleanup(find_value(lines, ALIASES["ชื่อมารดา"]))
    out["student_info"]["ชื่อสกุล"] = _cleanup(find_value(lines, ALIASES["ชื่อสกุล"]))

    first_name = ""
    for i, ln in enumerate(lines):
        if ln.startswith("ชื่อ ") and not ln.startswith("ชื่อสกุล"):
            if ("บิดา" not in ln) and ("มารดา" not in ln):
                first_name = ln.replace("ชื่อ", "", 1).strip()
                break
        if ln == "ชื่อ" and i + 1 < len(lines):
            cand = lines[i + 1].strip()
            if cand and ("ชื่อสกุล" not in cand) and ("บิดา" not in cand) and ("มารดา" not in cand):
                first_name = cand
                break
    out["student_info"]["ชื่อ"] = _cleanup(first_name)

    out["student_info"]["เลขประจำตัวนักเรียน"] = _cleanup(find_inline(lines, "เลขประจำตัวนักเรียน") or find_value(lines, ALIASES["เลขประจำตัวนักเรียน"]))
    out["student_info"]["เลขประจำตัวประชาชน"] = _cleanup(find_inline(lines, "เลขประจำตัวประชาชน") or find_value(lines, ALIASES["เลขประจำตัวประชาชน"]))

    born = find_value(lines, ALIASES["เกิดวันที่"]).replace("เดือน", "").replace("พ.ศ.", "").strip()
    out["student_info"]["เกิดวันที่"] = _cleanup(born)

    sex = ""
    nation = ""
    for ln in lines:
        if ln.startswith("เพศ") and ("สัญชาติ" in ln):
            m2 = re.search(r"เพศ\s*(.*?)\s*สัญชาติ\s*(.*)$", ln)
            if m2:
                sex = m2.group(1).strip()
                nation = m2.group(2).strip()
            break
    out["student_info"]["เพศ"] = _cleanup(sex)
    out["student_info"]["สัญชาติ"] = _cleanup(nation)

    out["student_info"]["เชื้อชาติ"] = _cleanup(find_value(lines, ALIASES["เชื้อชาติ"]))
    return out
