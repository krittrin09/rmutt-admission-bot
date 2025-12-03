from pdf2image import convert_from_path
from PIL import Image
import pytesseract
import os
import re


def run_ocr_on_image(img: Image.Image):
    """
    รับ PIL Image -> คืนเป็น text (string) และ lines (list)
    """
    try:
        # ใช้ภาษาไทย+อังกฤษ
        text = pytesseract.image_to_string(img, lang="tha+eng")
        # กรองบรรทัดว่างทิ้ง
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        return text, lines
    except Exception as e:
        print(f"❌ OCR Error: {e}")
        return "", []

def image_to_text(path):
    """
    path -> ถ้าเป็น PDF แปลงหน้าแรกเป็น image แล้ว OCR
    คืน: (text, lines:list)
    """
    if not os.path.exists(path):
        return "", []

    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".pdf":
            # แปลง PDF เป็นภาพ (เอาแค่หน้าแรกเพื่อความเร็ว)
            # poppler_path อาจต้องระบุถ้าบน Windows หรือ Server บางตัวหาไม่เจอ
            pages = convert_from_path(path, dpi=300)
            if not pages:
                return "", []
            img = pages[0]
            return run_ocr_on_image(img)
        else:
            # กรณีเป็นไฟล์รูปภาพ (jpg, png)
            img = Image.open(path)
            return run_ocr_on_image(img)
            
    except Exception as e:
        print(f"❌ Image Processing Error: {e}")
        return "", []

def extract_fields_from_lines(lines):
    """
    ตัวอย่างฟังก์ชันดึงข้อมูลแบบง่าย
    """
    data = {}
    for ln in lines:
        # ตัวอย่างการดึงเกรด
        if "เกรดเฉลี่ย" in ln or "GPA" in ln or "GPAX" in ln:
            data["gpa_raw"] = ln
        
        # ตัวอย่างการดึงชื่อ (ต้องปรับ logic ตามหน้าตาใบเกรดจริง)
        if "ชื่อ" in ln and "นามสกุล" not in ln:
            data.setdefault("name_lines", []).append(ln)
            
    return data
def result_view(request, pk):
    """
    แสดงผลลัพธ์ OCR ของ ID นั้นๆ (ถ้าต้องการ)
    """
    result = get_object_or_404(OCRResult, pk=pk)
    return render(request, "result.html", {"result": result})

def clean_ocr_text(text: str) -> str:
    """ล้าง OCR text ให้เรียบร้อย"""

    if not text:
        return ""

    # ลบช่องว่างเยอะเกิน
    text = re.sub(r"[ ]{2,}", " ", text)

    # บรรทัดติดกัน → บังคับขึ้นบรรทัดใหม่
    text = text.replace("•", "\n• ")

    # หากเจอประโยคที่ควรขึ้นบรรทัด (เช่น วัน เดือน ปี)
    text = re.sub(r"(\d{1,2}/\d{1,2}/\d{2,4})", r"\n\1\n", text)

    # Clean newline ซ้ำ
    text = re.sub(r"\n{2,}", "\n", text)

    return text.strip()