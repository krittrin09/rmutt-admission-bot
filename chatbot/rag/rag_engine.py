import os
from datetime import datetime
import pytz
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GENERAL_DB_PATH = os.path.join(BASE_DIR, "vector_db")

def get_rag_chain():
    try:
        # 1. วันที่ปัจจุบัน
        thai_tz = pytz.timezone('Asia/Bangkok')
        now = datetime.now(thai_tz)
        current_date_str = f"{now.day}/{now.month}/{now.year+543}"

        if not os.path.exists(GENERAL_DB_PATH):
            print("❌ ไม่พบ Database หลัก")
            return None

        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = FAISS.load_local(GENERAL_DB_PATH, embeddings, allow_dangerous_deserialization=True)
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", 
            google_api_key="AIzaSyDAcHGUbyeYbohdBd5os08nXn_9BduhtyM".strip(), # ⚠️ อย่าลืมใส่ API Key ของคุณที่นี่
            temperature=0.1
        )

        # 2. ⭐ แก้ไข Prompt: ลบตัวแปร {student_data} ออกจาก input_variables
        # แต่ยังคงไว้ใน string template เพราะเราจะยัด text เข้าไปใน {question} แทน
        template = f"""
        คุณเป็นเจ้าหน้าที่แนะแนวประจำ "คณะวิทยาศาสตร์และเทคโนโลยี" มทร.ธัญบุรี
        
        [ข้อมูลปัจจุบัน]
        - วันที่: {current_date_str}
        
        [ระเบียบการรับสมัคร (อ้างอิง)]
        {{context}}

        [ข้อมูลผู้สมัครและคำถาม]
        {{question}}
        
        [คำสั่งการตอบ]
        1. ให้วิเคราะห์ "ข้อมูลนักเรียน" (ที่แนบมาในคำถาม) เทียบกับ "ระเบียบการ" อย่างละเอียด
        2. ถ้าเกรดถึงเกณฑ์ ให้บอกว่า "สามารถสมัครได้" พร้อมระบุชื่อสาขา
        3. ถ้าเกรดไม่ถึง ให้บอกสาเหตุชัดเจน (เช่น เกรดคณิตต่ำกว่าเกณฑ์)
        4. หากผู้ใช้ถามเรื่องทั่วไป ให้ตอบตามระเบียบการ
        5. ใช้ภาษาที่เป็นกันเอง กระชับ
        6. ⚠️ **การจัดรูปแบบ:** - ห้ามนำตัวเลขข้อเดิมจากเอกสารมาตอบ (เช่น ห้ามตอบว่า '3. สาขา...') 
           - ให้ใช้ **Bullet Points (-)** แทนตัวเลขเสมอ เพื่อความสวยงาม
           - หรือถ้าระบุเป็นลำดับ ให้นับ 1, 2, 3 ใหม่เอง ห้ามข้ามเลข
        """
        
        QA_CHAIN_PROMPT = PromptTemplate(
            # ✅ จุดสำคัญ: ต้องเหลือแค่ context และ question เท่านั้น ห้ามมี student_data
            input_variables=["context", "question"],
            template=template,
        )

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=vectorstore.as_retriever(search_kwargs={"k": 15}),
            return_source_documents=False,
            chain_type_kwargs={"prompt": QA_CHAIN_PROMPT} 
        )
        
        return qa_chain

    except Exception as e:
        print(f"❌ RAG Engine Error: {e}")
        return None