import os
import re
from collections import defaultdict
from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# =====================================================
# PATH CONFIG
# =====================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, "chatbot", "rag", "data")
VECTOR_DB_PATH = os.path.join(BASE_DIR, "chatbot", "rag", "vector_db")

# =====================================================
# TXT PARSER (ตรงกับ overview.txt จริง)
# =====================================================
def parse_txt_file(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    documents = []

    # แยกตาม block หลักสูตร
    blocks = re.split(r"\n(?=มหาวิทยาลัย:)", raw)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        def extract(label):
            m = re.search(rf"{label}\s*:\s*(.+)", block)
            return m.group(1).strip() if m else ""

        university = extract("มหาวิทยาลัย")
        faculty = extract("คณะ")
        program = extract("หลักสูตร")
        major = extract("สาขาวิชา")
        program_id = extract("รหัสสาขา")
        round_name = extract("รอบการรับ")

        # ❌ ข้อมูลไม่ครบ ไม่เข้า RAG
        if not program_id or not round_name:
            continue

        documents.append(
            Document(
                page_content=block,
                metadata={
                    "program_id": program_id,
                    "major": major or program,
                    "round": round_name,
                    "faculty": faculty,
                    "university": university,
                    "source": os.path.basename(filepath),
                }
            )
        )

    return documents

# =====================================================
# MAIN INGEST FUNCTION
# =====================================================
def create_vector_db():
    print("🔄 เริ่ม Ingest ข้อมูลเข้า FAISS")

    if not os.path.exists(DATA_PATH):
        print("❌ ไม่พบโฟลเดอร์ data")
        return False

    documents_by_major = defaultdict(list)

    # อ่านทุกไฟล์ txt
    for filename in os.listdir(DATA_PATH):
        if filename.endswith(".txt"):
            filepath = os.path.join(DATA_PATH, filename)
            docs = parse_txt_file(filepath)

            for d in docs:
                # ใช้ prefix รหัสสาขาเป็น key (COM-01 → com)
                major_key = d.metadata["program_id"].split("-")[0].lower()
                documents_by_major[major_key].append(d)

    if not documents_by_major:
        print("❌ ไม่พบข้อมูลที่ parse ได้")
        return False

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"}
    )

    os.makedirs(VECTOR_DB_PATH, exist_ok=True)

    # =====================================================
    # BUILD FAISS PER MAJOR
    # =====================================================
    for major_key, docs in documents_by_major.items():
        major_path = os.path.join(VECTOR_DB_PATH, major_key)
        os.makedirs(major_path, exist_ok=True)

        # 👉 บันทึก source.txt ไว้ดูข้อมูลจริง
        with open(os.path.join(major_path, "source.txt"), "w", encoding="utf-8") as f:
            for d in docs:
                f.write(d.page_content)
                f.write("\n\n" + "=" * 80 + "\n\n")

        # 👉 สร้าง FAISS (เร็ว ไม่วน loop)
        db = FAISS.from_documents(docs, embeddings)
        db.save_local(major_path)

        print(f"✅ สร้าง FAISS สาขา '{major_key}' จำนวน {len(docs)} records")

    print("🎉 Ingest เสร็จสมบูรณ์ทุกสาขา")
    return True


# =====================================================
# RUN
# =====================================================
if __name__ == "__main__":
    create_vector_db()
