# OCR/Back_OCR/normalize.py
import re

CANONICAL_AREAS = [
    "ภาษาไทย",
    "คณิตศาสตร์",
    "วิทยาศาสตร์และเทคโนโลยี",
    "สังคมศึกษา ศาสนา และวัฒนธรรม",
    "สุขศึกษาและพลศึกษา",
    "ศิลปะ",
    "การงานอาชีพ",
    "ภาษาต่างประเทศ",
    "การศึกษาค้นคว้าด้วยตนเอง (IS)",
    "ผลการเรียนเฉลี่ยตลอดหลักสูตร",
]


def normalize_text(text: str) -> str:
    """basic cleanup"""
    text = text.strip()
    text = re.sub(r"\s+", "", text)
    return text


def normalize_learning_area(raw: str) -> str:
    raw_clean = normalize_text(raw)

    for canon in CANONICAL_AREAS:
        canon_clean = normalize_text(canon)
        if canon_clean in raw_clean or raw_clean in canon_clean:
            return canon

    return raw  # fallback: คืนค่าเดิมถ้าไม่ match
