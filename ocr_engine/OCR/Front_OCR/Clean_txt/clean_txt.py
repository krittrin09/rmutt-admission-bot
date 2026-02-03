# OCR/Front_OCR/Clean_txt/clean_txt.py

def clean_front_raw_text(text: str) -> str:
    """
    Clean raw OCR output from Front OCR.
    - ตัดคำว่า assistant ตัวที่สองออก
    - เอาเฉพาะเนื้อ OCR จริง
    """

    if not text:
        return ""

    # normalize newline
    text = text.replace("\r\n", "\n").strip()

    # -----------------------------
    # ตัด assistant ตัวที่สอง
    # -----------------------------
    if "assistant" in text:
        parts = text.split("assistant")
        text = parts[-1].strip()

    return text
