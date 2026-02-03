# OCR/Back_OCR/Clean_txt/clean_txt.py
import re


def clean_llm_output(text: str) -> str:
    """
    Clean raw text output from LLM.
    """

    if not text:
        return ""

    # 1) Remove markdown fences
    for bad in ["```json", "```", "`"]:
        text = text.replace(bad, "")

    # 2) Remove leading 'assistant' (single or multiple cases)
    text = re.sub(r"^\s*assistant[\s:]*", "", text, flags=re.IGNORECASE)

    # 3) If duplicated assistant exists, keep the last block
    blocks = re.split(r"\bassistant\b", text, flags=re.IGNORECASE)
    if len(blocks) > 2:
        text = blocks[-1]

    # 4) Final normalize
    return text.strip()
