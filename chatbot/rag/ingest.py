import os
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# กำหนด Path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data")         # โฟลเดอร์เก็บไฟล์ .txt ข้อมูลคณะ
VECTOR_DB_PATH = os.path.join(BASE_DIR, "vector_db") # โฟลเดอร์เก็บสมองหลัก

def create_vector_db():
    print(f"📂 เริ่มอ่านไฟล์ข้อมูลคณะจาก: {DATA_PATH}")
    
    # 1. ตรวจสอบว่ามีโฟลเดอร์ data ไหม
    if not os.path.exists(DATA_PATH):
        print("❌ ไม่พบโฟลเดอร์ data")
        return

    # 2. โหลดไฟล์ .txt ทั้งหมด
    loader = DirectoryLoader(DATA_PATH, glob="*.txt", loader_cls=TextLoader)
    documents = loader.load()
    
    if not documents:
        print("❌ ไม่พบไฟล์ .txt ในโฟลเดอร์ data เลย")
        return

    print(f"   - พบเอกสาร {len(documents)} ไฟล์")

    # 3. หั่นข้อความ
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = text_splitter.split_documents(documents)

    # 4. แปลงเป็น Vector
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    # 5. สร้างและบันทึก
    print("🧠 กำลังสร้าง Vector DB หลัก...")
    db = FAISS.from_documents(texts, embeddings)
    db.save_local(VECTOR_DB_PATH)
    print(f"✅ สร้าง Database หลักเสร็จแล้วที่: {VECTOR_DB_PATH}")

# ⭐ ต้องมีส่วนนี้ โปรแกรมถึงจะทำงานเมื่อสั่งรัน!
if __name__ == "__main__":
    create_vector_db()