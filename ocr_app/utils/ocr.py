# ocr_app/utils/ocr.py
import pytesseract
from PIL import Image
import re

# ถ้า tesseract ไม่ได้อยู่ใน PATH ปรับ pytesseract.pytesseract.tesseract_cmd
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

def image_to_text(path):
    """อ่านภาพด้วย Tesseract และคืน list ของบรรทัด (str)"""
    img = Image.open(path)
    text = pytesseract.image_to_string(img, lang='tha+eng')  # รวม Thai+English
    lines = [re.sub(r'\s+', ' ', l).strip() for l in text.splitlines() if l.strip()]
    return lines

def extract_fields_from_lines(lines):
    """heuristic ดึง gpax, gpamath, gpasci, gpalan, name, school"""
    data = {"gpax": None, "gpamath": None, "gpasci": None, "gpalan": None, "student_name": None, "school": None}
    for ln in lines:
        low = ln.lower()
        # หา GPAX: คำว่า 'ผลการเรียนเฉลี่ย' หรือ 'ผลการเรียนเฉลี่ยตลอดหลักสูตร'
        if 'ผลการเรียนเฉลี่ย' in low or 'ผลการเรียนเฉลี่ยตลอด' in low:
            m = re.search(r'([0-4]\.\d{1,2})', ln)
            if m:
                data['gpax'] = float(m.group(1))
        if 'คณิตศาสตร์' in low or 'คณิต' in low:
            m = re.search(r'([0-4]\.\d{1,2})', ln)
            if m:
                data['gpamath'] = float(m.group(1))
        if 'วิทยาศาสตร์' in low or 'วิทย์' in low:
            m = re.search(r'([0-4]\.\d{1,2})', ln)
            if m:
                data['gpasci'] = float(m.group(1))
        if 'ภาษาต่างประเทศ' in low or 'ภาษาต่างประเทศ' in low or 'ภาษาอังกฤษ' in low:
            m = re.search(r'([0-4]\.\d{1,2})', ln)
            if m:
                data['gpalan'] = float(m.group(1))
        if 'ชื่อ' in low and not data['student_name']:
            parts = ln.split('ชื่อ')
            if len(parts) > 1:
                data['student_name'] = parts[-1].strip()
        if 'โรงเรียน' in low and not data['school']:
            parts = ln.split('โรงเรียน')
            if len(parts) > 1:
                data['school'] = parts[-1].strip()
    # fallback: if gpax not found, pick max numeric 0-4
    if data['gpax'] is None:
        nums = []
        for ln in lines:
            for m in re.findall(r'([0-4]\.\d{1,2})', ln):
                nums.append(float(m))
        if nums:
            data['gpax'] = max(nums)
    return data
