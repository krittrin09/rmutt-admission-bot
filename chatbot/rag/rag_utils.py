import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def create_vector_db_from_text(text, session_id):
    """
    ฟังก์ชันนี้จะถูกเรียกใช้โดย views.py เมื่อมีการอัปโหลดรูป
    """
    # สร้างโฟลเดอร์แยกตาม Session ของผู้ใช้
    VECTOR_DB_PATH = os.path.join(BASE_DIR, "temp_rag", session_id, "vector_db")
    os.makedirs(VECTOR_DB_PATH, exist_ok=True)

    print(f"📂 สร้าง Vector DB ชั่วคราวสำหรับ Session: {session_id}")

    # หั่นข้อความจาก OCR
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = text_splitter.create_documents([text])

    # แปลงเป็น Vector
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # บันทึก
    db = FAISS.from_documents(texts, embeddings)
    db.save_local(VECTOR_DB_PATH)

    print(f"✅ บันทึก DB ส่วนตัวสำเร็จที่: {VECTOR_DB_PATH}")
    return VECTOR_DB_PATH

# ... (โค้ดเดิมที่มี create_vector_db_from_text) ...

# ✅ เพิ่มฟังก์ชันนี้ต่อท้ายไฟล์ครับ
def has_vector_db(session_id):
    """
    เช็คว่า Session นี้มี Vector DB แล้วหรือยัง?
    """
    VECTOR_DB_PATH = os.path.join(BASE_DIR, "temp_rag", session_id, "vector_db")
    return os.path.exists(VECTOR_DB_PATH)