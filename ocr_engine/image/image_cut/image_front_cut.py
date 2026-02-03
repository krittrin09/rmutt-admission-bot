import cv2
from PIL import Image


def process_front_image(
    img_path: str,
    target_long_side: int = 1800,
    crop_bottom_ratio: float = 0.30
) -> Image.Image:
    """
    Preprocess + crop header for Front OCR.

    - Resize so the longest side = target_long_side
    - Crop header (top part of page)
    - Return PIL.Image (RGB)

    Args:
        img_path (str): path to front transcript image
        target_long_side (int): normalize size (default 1800)
        crop_bottom_ratio (float): portion of height to keep from top (default 0.30)

    Returns:
        PIL.Image.Image
    """

    # 1) Read image
    img = cv2.imread(img_path)
    if img is None:
        raise ValueError(f"Cannot read image: {img_path}")

    # 2) Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 3) Resize (normalize scale)
    h, w = gray.shape
    scale = target_long_side / max(h, w)

    resized = cv2.resize(
        gray,
        (int(w * scale), int(h * scale)),
        interpolation=cv2.INTER_LINEAR
    )

    # 4) Convert to PIL RGB (model expects RGB)
    pil_img = Image.fromarray(resized).convert("RGB")

    # 5) Crop header
    W, H = pil_img.size
    cropped = pil_img.crop((
        0,
        0,
        W,
        int(H * crop_bottom_ratio)
    ))

    return cropped
