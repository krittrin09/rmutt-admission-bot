# ocr_engine/main_back_pipeline.py
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .config import BACK_OCR_RESULT_DIR
from .image.image_cut.image_back_cut import process_back_image
from .OCR.Back_OCR.Back_OCR import run_back_ocr
from .OCR.Back_OCR.parse_table import parse_table


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def fmt_sec(sec: float) -> str:
    if sec < 60:
        return f"{sec:.3f}s"
    m = int(sec // 60)
    s = sec - m * 60
    return f"{m}m {s:.3f}s"


def run_back_pipeline(
    image_path: str,
    model,
    processor,
    device,
    save_files: bool = True,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    ใช้ใน Django ได้:
    - รับ image_path (ไฟล์ที่ user upload แล้ว Django save ไว้ใน media)
    - รับ model/processor/device ที่ "โหลดไว้แล้ว" จากภายนอก (สำคัญ)
    - คืนผล parsed JSON (dict)
    - optional: save raw html + json ลง BACK_OCR_RESULT_DIR
    """
    img_path = Path(image_path)
    if not img_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    out_dir = Path(BACK_OCR_RESULT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = now_stamp()
    t_total_start = time.perf_counter()

    # 1) preprocess
    t1 = time.perf_counter()
    image = process_back_image(str(img_path))
    dt1 = time.perf_counter() - t1

    # 2) load model (REMOVED)
    #    ❌ ห้าม load_model() ใน pipeline อีกแล้ว
    dt2 = 0.0

    # 3) run OCR
    t3 = time.perf_counter()
    raw_html = run_back_ocr(image=image, model=model, processor=processor, device=device)
    dt3 = time.perf_counter() - t3

    # 4) parse
    t4 = time.perf_counter()
    parsed = parse_table(raw_html)
    dt4 = time.perf_counter() - t4

    raw_path = None
    json_path = None

    if save_files:
        raw_path = out_dir / f"{stamp}_back_ocr_raw.html"
        raw_path.write_text(raw_html, encoding="utf-8")

        json_path = out_dir / f"{stamp}_back_ocr_parsed.json"
        json_path.write_text(
            json.dumps(parsed, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    t_total = time.perf_counter() - t_total_start

    if verbose:
        print("=== BACK OCR PIPELINE ===")
        print("Preprocess:", fmt_sec(dt1))
        print("Load model:", fmt_sec(dt2), "(preloaded)")
        print("Run OCR   :", fmt_sec(dt3))
        print("Parse     :", fmt_sec(dt4))
        print("TOTAL     :", fmt_sec(t_total))
        if raw_path:
            print("Saved:", raw_path)
        if json_path:
            print("Saved:", json_path)

    return {
        "parsed": parsed,
        "meta": {
            "device": str(device),
            "timing": {
                "preprocess": dt1,
                "load_model": dt2,
                "run_ocr": dt3,
                "parse": dt4,
                "total": t_total,
            },
            "saved_files": {
                "raw_html": str(raw_path) if raw_path else None,
                "json": str(json_path) if json_path else None,
            },
            "input_image": str(img_path),
        },
    }


# เผื่ออยากรันแบบสคริปต์: ต้อง preload model เองก่อน
if __name__ == "__main__":
    from .model_loader import load_model

    model, processor, device = load_model()
    test_image = str((Path(__file__).resolve().parent / "image" / "back").glob("*").__iter__().__next__())
    print(run_back_pipeline(test_image, model=model, processor=processor, device=device, save_files=True, verbose=True))
