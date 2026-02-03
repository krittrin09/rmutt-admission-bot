from OCR.Front_OCR.schemas import FRONT_SCHEMA
from copy import deepcopy
import re

def text_lines_to_json(lines: list[str]) -> dict:
    data = deepcopy(FRONT_SCHEMA)

    # header
    for l in lines:
        if l.startswith("ระเบียนแสดงผล"):
            data["document_info"]["ประเภทเอกสาร"] = l
        if l.startswith("ปพ."):
            m = re.search(r"(ปพ\.\d).*?ชุดที่\s*(\d+)\s*เลขที่\s*(\d+)", l)
            if m:
                data["document_info"]["ปพ"] = m.group(1)
                data["document_info"]["ชุดที่"] = m.group(2)
                data["document_info"]["เลขที่"] = m.group(3)

    field_map = {
        "โรงเรียน": ("school_info", "โรงเรียน"),
        "สังกัด": ("school_info", "สังกัด"),
        "ตำบล/แขวง": ("school_info", "ตำบล/แขวง"),
        "อำเภอ/เขต": ("school_info", "อำเภอ/เขต"),
        "จังหวัด": ("school_info", "จังหวัด"),
        "สำนักงานเขตพื้นที่การศึกษา": ("school_info", "สำนักงานเขตพื้นที่การศึกษา"),
        "วันที่เข้าเรียน": ("school_info", "วันเข้าเรียน"),
        "โรงเรียนเดิม": ("school_info", "โรงเรียนเดิม"),
        "ชั้นเรียนสุดท้าย": ("school_info", "ชั้นเรียนสุดท้าย"),

        "ชื่อ": ("student_info", "ชื่อ"),
        "ชื่อสกุล": ("student_info", "ชื่อสกุล"),
        "เลขประจำตัวนักเรียน": ("student_info", "เลขประจำตัวนักเรียน"),
        "เลขประจำตัวประชาชน": ("student_info", "เลขประจำตัวประชาชน"),
        "เพศ": ("student_info", "เพศ"),
        "สัญชาติ": ("student_info", "สัญชาติ"),
        "ศาสนา": ("student_info", "ศาสนา"),
        "ชื่อ - ชื่อสกุลบิดา": ("student_info", "ชื่อ-ชื่อสกุลบิดา"),
        "ชื่อ - ชื่อสกุลมารดา": ("student_info", "ชื่อ-ชื่อสกุลมารดา"),
    }

    for l in lines:
        if l.startswith("วันเกิด"):
            data["student_info"]["เกิดวันที่"] = (
                l.replace("วันเกิด", "").replace("เดือน", "").replace("พ.ศ.", "").strip()
            )
            continue

        for k, (sec, key) in field_map.items():
            if l.startswith(k):
                data[sec][key] = l.replace(k, "", 1).strip()

    # จังหวัดโรงเรียนเดิม
    found = False
    for l in lines:
        if l.startswith("โรงเรียนเดิม"):
            found = True
            continue
        if found and l.startswith("จังหวัด"):
            data["school_info"]["จังหวัดโรงเรียนเดิม"] = l.replace("จังหวัด", "").strip()
            break

    return data
