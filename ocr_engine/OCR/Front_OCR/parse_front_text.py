from OCR.Front_OCR.Clean_txt.debug_text_lines import debug_text_lines
from OCR.Front_OCR.Clean_txt.text_to_json import text_lines_to_json

def parse_front_text(clean_text: str) -> dict:
    lines = debug_text_lines(clean_text)
    json_data = text_lines_to_json(lines)
    return json_data
