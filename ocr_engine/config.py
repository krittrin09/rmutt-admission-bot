# ocr_engine/config.py
from pathlib import Path

# โฟลเดอร์ ocr_engine (…/admission_system/ocr_engine)
ENGINE_ROOT = Path(__file__).resolve().parent

# เผื่อคุณอยากชี้ไปที่โฟลเดอร์หลัก Django ด้วย
DJANGO_ROOT = ENGINE_ROOT.parent

# -------------------------
# Image paths (ถ้ายังใช้เป็นโฟลเดอร์ตัวอย่าง)
# -------------------------
IMAGE_BACK_DIR = ENGINE_ROOT / "image" / "back"
IMAGE_FRONT_DIR = ENGINE_ROOT / "image" / "front"

# -------------------------
# Model path
# -------------------------
MODEL_DIR = ENGINE_ROOT / "model_typhoon"

# -------------------------
# OCR result paths
# -------------------------
BACK_OCR_RESULT_DIR = DJANGO_ROOT / "media" / "temp" / "Back_json"
FRONT_OCR_RESULT_DIR = DJANGO_ROOT / "media" / "temp" / "Front_json"
