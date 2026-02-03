# ocr_engine/main_front_pipline.py
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from PIL import Image

from ocr_engine.config import FRONT_OCR_RESULT_DIR
from ocr_engine.image.image_cut.image_front_cut import process_front_image
from ocr_engine.OCR.Front_OCR.Front_OCR import run_front_ocr
from ocr_engine.OCR.Front_OCR.Clean_txt.clean_txt import clean_front_raw_text
from ocr_engine.OCR.Front_OCR.parse_front_v2 import parse_front_clean_text_to_json


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def fmt_sec(sec: float) -> str:
    if sec < 60:
        return f"{sec:.3f}s"
    m = int(sec // 60)
    s = sec - m * 60
    return f"{m}m {s:.3f}s"


def run_front_pipeline(
    image_path: str,
    model,
    processor,
    device,
    save_files: bool = True,
    verbose: bool = False,
) -> Dict[str, Any]:

    img_path = Path(image_path)
    if not img_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    out_dir = Path(FRONT_OCR_RESULT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = now_stamp()
    t_total_start = time.perf_counter()

    # 1) preprocess
    t1 = time.perf_counter()
    image: Image.Image = process_front_image(str(img_path))
    dt1 = time.perf_counter() - t1

    # 2) load model (REMOVED) -> ต้อง preload จาก service.py
    dt2 = 0.0

    # 3) run OCR
    t3 = time.perf_counter()
    raw_text = run_front_ocr(image=image, model=model, processor=processor, device=device)
    dt3 = time.perf_counter() - t3

    # 4) clean
    t4 = time.perf_counter()
    clean_text = clean_front_raw_text(raw_text)
    dt4 = time.perf_counter() - t4

    # 5) parse
    t5 = time.perf_counter()
    parsed = parse_front_clean_text_to_json(clean_text)
    dt5 = time.perf_counter() - t5

    clean_path = None
    json_path = None

    if save_files:
        clean_path = out_dir / f"{stamp}_front_ocr_clean.txt"
        clean_path.write_text(clean_text, encoding="utf-8")

        json_path = out_dir / f"{stamp}_front_ocr_parsed.json"
        json_path.write_text(
            json.dumps(parsed, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    t_total = time.perf_counter() - t_total_start

    if verbose:
        print("=== FRONT OCR PIPELINE ===")
        print("Preprocess:", fmt_sec(dt1))
        print("Load model:", fmt_sec(dt2), "(preloaded)")
        print("Run OCR   :", fmt_sec(dt3))
        print("Clean     :", fmt_sec(dt4))
        print("Parse     :", fmt_sec(dt5))
        print("TOTAL     :", fmt_sec(t_total))
        if clean_path:
            print("Saved:", clean_path)
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
                "clean": dt4,
                "parse": dt5,
                "total": t_total,
            },
            "saved_files": {
                "clean_txt": str(clean_path) if clean_path else None,
                "json": str(json_path) if json_path else None,
            },
            "input_image": str(img_path),
        },
    }
