# image_cut/image_back_cut.py
import cv2
from PIL import Image


def process_back_image(img_path: str) -> Image.Image:
    """
    Read image from path, preprocess, and crop ROI for back transcript.
    Return PIL.Image for OCR.
    """

    # 1) Read image
    img = cv2.imread(img_path)
    if img is None:
        raise ValueError(f"Cannot read image: {img_path}")

    # 2) Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 3) Resize (normalize scale)
    h, w = gray.shape
    target_long_side = 1800
    scale = target_long_side / max(h, w)

    resized = cv2.resize(
        gray,
        (int(w * scale), int(h * scale)),
        interpolation=cv2.INTER_LINEAR
    )

    # 4) Convert to PIL RGB (VLM expects RGB)
    pil_img = Image.fromarray(resized).convert("RGB")

    # 5) Crop ROI (ปรับตามที่คุณใช้ใน Colab)
    W, H = pil_img.size

    cropped = pil_img.crop((
        int(W * 0.65),   # left
        int(H * 0.35),   # top
        int(W * 1.00),   # right
        int(H * 0.58),   # bottom
    ))

    return cropped
