# ocr_engine/model_loader.py
import torch
from transformers import AutoProcessor, AutoModelForImageTextToText

from .config import MODEL_DIR  # ✅ ใช้ path กลางจาก config.py

BASE_MODEL_ID = "scb10x/typhoon-ocr-3b"

def load_model():
    device = "cuda" if torch.cuda.is_available() else "cpu"

    processor = AutoProcessor.from_pretrained(
        BASE_MODEL_ID,
        trust_remote_code=True
    )

    dtype = torch.float16 if device == "cuda" else torch.float32

    model = AutoModelForImageTextToText.from_pretrained(
        str(MODEL_DIR),  # ✅ แทน hardcode E:\... ให้เป็น path ที่ portable
        trust_remote_code=True,
        dtype=dtype,
        device_map="auto" if device == "cuda" else None,
    )

    if device == "cpu":
        model.to(device)

    model.eval()
    return model, processor, device
