import os
from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VECTOR_DB_PATH = os.path.join(BASE_DIR, "vector_db")


def create_vector_db_from_text(text: str) -> bool:
    """
    ใช้สำหรับ OCR → text → update RAG
    """
    try:
        if not text.strip():
            return False

        documents = [
            Document(
                page_content=text,
                metadata={"source": "ocr_upload"}
            )
        ]

        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
        )

        db = FAISS.from_documents(documents, embeddings)
        db.save_local(VECTOR_DB_PATH)

        print("✅ OCR Vector DB created")
        return True

    except Exception as e:
        print(f"❌ OCR RAG error: {e}")
        return False
