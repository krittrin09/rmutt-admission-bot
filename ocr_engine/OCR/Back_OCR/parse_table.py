# OCR/Back_OCR/parse_table.py

import re
import json
from typing import Dict, List, Optional
from bs4 import BeautifulSoup


def parse_table(raw_text: str) -> Dict[str, List[Dict[str, Optional[float]]]]:
    """
    Parse learning area table from OCR output.

    รองรับ:
    - JSON ที่มี key "html"
    - JSON ที่มี key "table" (markdown)
    - string HTML / markdown ตรง ๆ
    """

    text = raw_text.strip()

    # ------------------------------------
    # STEP 1: ถ้าเป็น JSON → ดึง content ออกมาก่อน
    # ------------------------------------
    if text.startswith("{"):
        try:
            data = json.loads(text)
            if "html" in data:
                text = data["html"]
            elif "table" in data:
                text = data["table"]
        except json.JSONDecodeError:
            pass  # ถ้า parse ไม่ได้ ถือว่าเป็น raw text

    # ------------------------------------
    # STEP 2: CASE HTML TABLE
    # ------------------------------------
    if "<table" in text.lower():
        match = re.search(r"<table[\s\S]*?</table>", text, re.IGNORECASE)
        if not match:
            return {"learning_areas": []}

        soup = BeautifulSoup(match.group(0), "html.parser")
        rows = []

        for tr in soup.find_all("tr"):
            cols = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(cols) == 3:
                area, credit, gpa = cols
                rows.append({
                    "กลุ่มสาระการเรียนรู้": area,
                    "หน่วยกิตรวม": _to_float(credit),
                    "ผลการเรียนเฉลี่ย": _to_float(gpa),
                })

        return {"learning_areas": rows}

    # ------------------------------------
    # STEP 3: CASE MARKDOWN TABLE
    # ------------------------------------
    if "|" in text:
        lines = [
            line for line in text.splitlines()
            if line.count("|") >= 2 and "---" not in line
        ]

        rows = []
        for line in lines:
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) == 3:
                area, credit, gpa = parts
                rows.append({
                    "กลุ่มสาระการเรียนรู้": area,
                    "หน่วยกิตรวม": _to_float(credit),
                    "ผลการเรียนเฉลี่ย": _to_float(gpa),
                })

        return {"learning_areas": rows}

    # ------------------------------------
    # STEP 4: fallback
    # ------------------------------------
    return {"learning_areas": []}


def _to_float(value: str) -> Optional[float]:
    """
    Convert string to float safely.
    """
    try:
        return float(value)
    except:
        return None
