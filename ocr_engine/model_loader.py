from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
import torch
from .config import MODEL_DIR

BASE_MODEL_ID = "scb10x/typhoon-ocr-3b"

def load_model():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    processor = AutoProcessor.from_pretrained(
        BASE_MODEL_ID,
        trust_remote_code=True
    )

    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        str(MODEL_DIR),
        trust_remote_code=True,
        torch_dtype=dtype,
        device_map="auto" if device == "cuda" else None,
    )

    # 🔑 FIX ที่ถูกต้องสำหรับ Qwen2.5-VL
    model.lm_head.weight = model.model.language_model.embed_tokens.weight

    if device == "cpu":
        model.to(device)

    model.eval()
    return model, processor, device
