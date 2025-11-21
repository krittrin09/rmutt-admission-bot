import os
from django.conf import settings

# Import แบบมาตรฐาน (หลังจาก Force Install แล้ว บรรทัดนี้ต้องผ่าน)
from langchain.chains import RetrievalQA 
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.llms import Ollama 

def get_rag_chain():
    db_path = os.path.join(settings.BASE_DIR, 'chatbot', 'rag', 'vector_db')
    
    if not os.path.exists(db_path):
        print(f"Warning: Vector DB path not found: {db_path}")
        return None

    try:
        # 1. Embeddings
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
        
        # 2. Load Vector DB
        vector_db = FAISS.load_local(
            db_path, 
            embeddings, 
            allow_dangerous_deserialization=True
        )
        
        # 3. Setup LLM
        llm = Ollama(model="typhoon") 

        # 4. Create Chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vector_db.as_retriever(search_kwargs={"k": 3}),
            return_source_documents=False
        )
        return qa_chain

    except Exception as e:
        print(f"Error initializing RAG: {e}")
        return None