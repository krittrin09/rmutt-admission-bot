from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

DATA_PATH = "chatbot/rag/data/admission.txt"
DB_PATH = "chatbot/rag/vector_db"

loader = TextLoader(DATA_PATH, encoding="utf-8")
documents = loader.load()

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)

docs = splitter.split_documents(documents)

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)

db = FAISS.from_documents(docs, embeddings)
db.save_local(DB_PATH)

print("✅ สร้าง Vector DB สำเร็จแล้ว")
