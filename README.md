# RMUTT CSI Admission Chatbot 🤖🎓

## ✨ ฟีเจอร์หลัก
* **AI Chatbot:** ตอบคำถามเกณฑ์การรับสมัครได้อย่างแม่นยำโดยอ้างอิงจากระเบียบการล่าสุด
* **Transcript OCR:** รองรับการอัปโหลดใบ ปพ.1 (รูปภาพ/PDF) เพื่อดึงเกรดและตรวจสอบคุณสมบัติอัตโนมัติ
* **Interactive UI:** หน้าจอแชทสวยงาม ใช้งานง่าย รองรับทั้ง Desktop และ Mobile
* **Smart Context:** ระบบจดจำข้อมูลผู้ใช้ (Session) ทำให้บทสนทนาต่อเนื่อง

## 🛠️ เทคโนโลยีที่ใช้ (Tech Stack)
* **Backend:** Django (Python)
* **AI Model:** qwen2.5:1.5b (via LangChain)
* **Vector DB:** FAISS (สำหรับระบบ RAG)
* **OCR:** Tesseract OCR + Poppler (pdf2image)
* **Frontend:** HTML5, CSS3, Bootstrap 5, JavaScript (AJAX)

## ⚙️ การติดตั้งและรันโปรเจกต์ (Installation)

1.  **Clone โปรเจกต์**
    ```bash
    git clone [https://github.com/krittrin09/rmutt-admission-bot.git](https://github.com/krittrin09/rmutt-admission-bot.git)
    cd rmutt-admission-bot
    ```

2.  **สร้าง Virtual Environment**
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Mac/Linux
    source .venv/bin/activate
    ```

3.  **ติดตั้ง Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **ติดตั้งโปรแกรมระบบ (System Requirements)**
    * ต้องติดตั้ง **Tesseract OCR** และ **Poppler** ลงในเครื่องก่อน (สำหรับฟีเจอร์ OCR)
    * *Linux (Ubuntu):* `sudo apt-get install tesseract-ocr tesseract-ocr-tha poppler-utils`
    * *Windows:* ดาวน์โหลดตัวติดตั้ง Tesseract และ Poppler และตั้งค่า Path

5.  **ตั้งค่า API Key**
    * แก้ไขไฟล์ `chatbot/rag/rag_engine.py` (หรือสร้างไฟล์ .env) เพื่อใส่ **Google Gemini API Key**

6.  **สร้างฐานข้อมูลความรู้ (Ingest)**
    ```bash
    python chatbot/rag/ingest.py
    ```

7.  **รัน Server**
    * **สำหรับ Dev:** `python manage.py runserver`
    * **สำหรับ Production:**
        ```bash
        gunicorn admission_system.wsgi:application --bind 0.0.0.0:8000 --workers 4 --threads 2 --timeout 120
        ```

## 📂 โครงสร้างโฟลเดอร์
* `chatbot/`: ระบบแชทและ RAG Engine
* `ocr_app/`: ระบบอัปโหลดและประมวลผลภาพ
* `media/`: (Local Only) ไฟล์ที่ผู้ใช้อัปโหลด
* `templates/`: ไฟล์ HTML หลัก

---
**Developed by:** Noah Krittrin
