# 🎓 RMUTT Admission AI Chatbot (RAG System)

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=chainlink&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white)

**โปรเจกต์แชทบอทอัจฉริยะสำหรับตอบคำถามระเบียบการรับสมัครนักศึกษา** พัฒนาขึ้นเพื่อช่วยให้ผู้สมัครสามารถเข้าถึงข้อมูลเกณฑ์การรับเข้าศึกษาต่อได้อย่างรวดเร็ว แม่นยำ และทำงานได้ตลอด 24 ชั่วโมง โดยประยุกต์ใช้เทคโนโลยี Generative AI ร่วมกับระบบ RAG (Retrieval-Augmented Generation) เพื่อลดการตอบคำถามผิดพลาด (Hallucination) ของ AI

---

## ✨ ฟีเจอร์หลัก (Key Features)

* 🤖 **RAG-Powered AI Chatbot:** ตอบคำถามเกณฑ์การรับสมัครได้อย่างแม่นยำ โดยดึงบริบทอ้างอิงจากฐานข้อมูลเอกสารระเบียบการจริงของมหาวิทยาลัย
* 📄 **Automated Transcript OCR:** รองรับการอัปโหลดไฟล์ใบแสดงผลการเรียน (ปพ.1) ทั้งรูปแบบรูปภาพและ PDF เพื่อดึงเกรดเฉลี่ย (GPAX) และตรวจสอบคุณสมบัติเบื้องต้นอัตโนมัติ
* 💬 **Smart Context & Session:** ระบบจดจำบริบทการสนทนาของผู้ใช้ (Chat History) ทำให้สามารถถาม-ตอบต่อเนื่องได้อย่างเป็นธรรมชาติ
* 📱 **Interactive & Responsive UI:** หน้าต่างแชทออกแบบให้ใช้งานง่าย สวยงาม และรองรับการแสดงผลทั้งบน Desktop และ Mobile

---

## 🏗️ สถาปัตยกรรมระบบ (System Architecture)

* **LLM Engine:** รันโมเดล `qwen2.5:1.5b` แบบ Local ผ่าน **Ollama** (ช่วยประหยัดต้นทุนและรักษาความปลอดภัยของข้อมูล)
* **RAG Framework:** ใช้ **LangChain** ในการจัดการ Flow ของ Prompt และเชื่อมต่อกับ **FAISS** (Vector Database) เพื่อค้นหาข้อมูลที่เกี่ยวข้องที่สุดมาตอบคำถาม
* **OCR System:** ใช้ **Tesseract OCR** ทำงานร่วมกับ **Poppler** (pdf2image) ในการสกัดข้อความจากเอกสาร
* **Web Framework:** พัฒนาระบบหลังบ้านและ API ด้วย **Django** พร้อมส่วนแสดงผล (Frontend) ด้วย HTML5, CSS3, Bootstrap 5 และ JavaScript (AJAX)

---

## ⚙️ การติดตั้งและรันโปรเจกต์ (Installation Guide)

### 1. โคลนโปรเจกต์และเตรียมสภาพแวดล้อม
```bash
git clone [https://github.com/krittrin09/rmutt-admission-bot.git](https://github.com/krittrin09/rmutt-admission-bot.git)
cd rmutt-admission-bot

# สร้างและเปิดใช้งาน Virtual Environment
python -m venv .venv

# สำหรับ Windows
.venv\Scripts\activate
# สำหรับ Mac/Linux
source .venv/bin/activate
