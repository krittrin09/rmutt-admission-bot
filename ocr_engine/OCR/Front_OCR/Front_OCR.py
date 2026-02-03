# OCR/Front_OCR/Front_OCR.py
import torch

def run_front_ocr(image, model, processor, device: str = "cpu") -> str:
    """
    Front OCR (RAW TEXT ONLY)

    image      : PIL.Image
    model      : Qwen2.5-VL
    processor  : AutoProcessor
    device     : cpu

    return     : raw text (str)
    """

    schema = """
ให้ตอบกลับเป็น JSON เท่านั้น ห้ามมีข้อความอื่นทั้งหน้าและหลัง JSON
ห้าม escape เครื่องหมายเกินจำเป็น
ค่าที่เป็นตัวเลขให้ตอบเป็น string เท่านั้น
ใช้ schema เท่านี้ ห้ามเพิ่มหรือลด key:

{
    "document_info": {
        "ประเภทเอกสาร": "",
        "ปพ": "",
        "ชุดที่": "",
        "เลขที่": ""
    },
    "school_info": {
        "โรงเรียน": "",
        "สังกัด": "",
        "ตำบล/แขวง": "",
        "อำเภอ/เขต": "",
        "จังหวัด": "",
        "สำนักงานเขตพื้นที่การศึกษา": "",
        "วันเข้าเรียน": "",
        "โรงเรียนเดิม": "",
        "จังหวัดโรงเรียนเดิม": "",
        "ชั้นเรียนสุดท้าย": ""
    },
    "student_info": {
        "ชื่อ": "",
        "ชื่อสกุล": "",
        "เลขประจำตัวนักเรียน": "",
        "เลขประจำตัวประชาชน": "",
        "เกิดวันที่": "",
        "เพศ": "",
        "สัญชาติ": "",
        "เชื้อชาติ": "",
        "ศาสนา": "",
        "ชื่อ-ชื่อสกุลบิดา": "",
        "ชื่อ-ชื่อสกุลมารดา": ""
    }
}
"""
    conversation = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {
                    "type": "text",
                    "text": (
                        "อ่านข้อความทั้งหมดจากเอกสารนี้ให้ครบถ้วน"
                        "อ่านถึงคำว่าผลการเรียนรายวิชา"
                        "เรียงตามที่เห็นในภาพ "
                        "ไม่ต้องสรุป " + schema
                    )
                },
            ],
        }
    ]

    prompt = processor.apply_chat_template(
        conversation,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = processor(
        text=[prompt],
        images=[image],
        return_tensors="pt"
    )

    # move to cpu
    for k in inputs:
        inputs[k] = inputs[k].to(device)

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=2048,
            do_sample=False,
            temperature=0.0,
            eos_token_id=processor.tokenizer.eos_token_id,
        )

    raw_text = processor.decode(
        output[0],
        skip_special_tokens=True
    )

    return raw_text
