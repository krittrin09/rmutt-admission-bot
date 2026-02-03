# OCR/Back_OCR/Back_OCR.py
import torch
from .Clean_txt.clean_txt import clean_llm_output
from .schemas import BACK_LEARNING_AREAS_SCHEMA

# =====================================================
# SCHEMA (คัดตรงจาก Colab ไม่แก้ข้อความ)
# =====================================================

SCHEMA = """
อ่านข้อมูลเฉพาะจาก 'ตารางกลุ่มสาระการเรียนรู้/การศึกษาค้นคว้าด้วยตนเอง'

ให้ตอบออกมาเป็น HTML <table> เท่านั้น
รูปแบบที่อนุญาต:
<table>
<tr><td>ภาษาไทย</td><td>11.0</td><td>3.81</td></tr>
<tr><td>คณิตศาสตร์</td><td>18.0</td><td>2.33</td></tr>
...
</table>

กลุ่มสาระการเรียนรู้ที่ควรพบในเอกสาร ได้แก่:

- ภาษาไทย
- คณิตศาสตร์
- วิทยาศาสตร์และเทคโนโลยี
- สังคมศึกษา ศาสนา และวัฒนธรรม
- สุขศึกษาและพลศึกษา
- ศิลปะ
- การงานอาชีพ
- ภาษาต่างประเทศ
- การศึกษาค้นคว้าด้วยตนเอง (IS)
- ผลการเรียนเฉลี่ยตลอดหลักสูตร

กติกา:
- ห้ามตอบ JSON เด็ดขาด
- ห้ามตอบ Markdown table เช่น | วิชา | ...
- ใช้เฉพาะ HTML <table>, <tr>, <td>
- ห้ามมี <thead> หรือ <tbody>
- แต่ละแถวต้องมี 3 <td>: กลุ่มสาระ | หน่วยกิตรวม | ผลการเรียนเฉลี่ย
- ถ้าอ่านไม่ชัด หรือเป็น "-" ให้ใช้ <td></td>
- เรียงข้อมูลตามลำดับแถวจริงในเอกสาร
- ห้ามอธิบายเพิ่มเติม
"""


# =====================================================
# MAIN OCR FUNCTION 
# =====================================================

def run_back_ocr(image, model, processor, device):
    """
    Run OCR for back transcript learning area table.
    image      : PIL.Image
    model      : Qwen2.5-VL model
    processor  : AutoProcessor
    device     : 'cpu'
    return     : cleaned HTML table (str)
    """

    # -------------------------------
    # 1) Qwen2.5-VL conversation
    # -------------------------------
    conversation = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {
                    "type": "text",
                    "text": (
                        "อ่านข้อมูลเฉพาะจากตาราง "
                        "'กลุ่มสาระการเรียนรู้/การศึกษาค้นคว้าด้วยตนเอง' "
                        "และตอบเป็น HTML table เท่านั้น:\n\n"
                        + SCHEMA
                    )
                },
            ],
        }
    ]

    # -------------------------------
    # 2) Build prompt
    # -------------------------------
    prompt = processor.apply_chat_template(
        conversation,
        tokenize=False,
        add_generation_prompt=True,
    )

    # -------------------------------
    # 3) Prepare inputs
    # -------------------------------
    inputs = processor(
        text=[prompt],
        images=[image],
        return_tensors="pt"
    )

    # move tensors to device (CPU safe)
    for k in inputs:
        inputs[k] = inputs[k].to(device)

    # -------------------------------
    # 4) Generate
    # -------------------------------
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=800,
            do_sample=False,
            temperature=0.0,
            repetition_penalty=1.05,
            eos_token_id=processor.tokenizer.eos_token_id,
        )

    # -------------------------------
    # 5) Decode
    # -------------------------------
    raw_text = processor.decode(
        out[0],
        skip_special_tokens=True
    )

    # -------------------------------
    # 6) Clean text 
    # -------------------------------
    clean_text = clean_llm_output(raw_text)

    return clean_text
