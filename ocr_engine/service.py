import os
from ocr_engine.main_back_pipeline import run_back_pipeline
from ocr_engine.main_front_pipline import run_front_pipeline  # ✅ เพิ่ม
from ocr_engine.model_loader import load_model

# Lazy-loaded singletons
_MODEL = None
_PROCESSOR = None
_DEVICE = None


def get_model():
    """Load model/processor once, on first use."""
    global _MODEL, _PROCESSOR, _DEVICE
    if _MODEL is None:
        _MODEL, _PROCESSOR, _DEVICE = load_model()
    return _MODEL, _PROCESSOR, _DEVICE


def run_back_ocr_from_image(image_path: str, **kwargs):
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    model, processor, device = get_model()
    return run_back_pipeline(
        image_path=image_path,
        model=model,
        processor=processor,
        device=device,
        **kwargs
    )


def run_back_ocr_from_temp_filename(temp_image_path: str, **kwargs):
    """
    Wrapper สำหรับกรณี view ส่ง path ของไฟล์ชั่วคราวเข้ามา
    (ชื่อฟังก์ชันนี้จำเป็น เพราะ ocr_app/views.py import ชื่อนี้)
    """
    return run_back_ocr_from_image(temp_image_path, **kwargs)


# =========================
# ✅ FRONT (เพิ่มใหม่)
# =========================
def run_front_ocr_from_image(image_path: str, **kwargs):
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    model, processor, device = get_model()
    return run_front_pipeline(
        image_path=image_path,
        model=model,
        processor=processor,
        device=device,
        **kwargs
    )


def run_front_ocr_from_temp_filename(temp_image_path: str, **kwargs):
    """
    Wrapper สำหรับกรณี view ส่ง path ของไฟล์ชั่วคราวเข้ามา (เหมือน back)
    """
    return run_front_ocr_from_image(temp_image_path, **kwargs)
