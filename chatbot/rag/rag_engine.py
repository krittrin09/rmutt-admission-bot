import os
import re
import logging
from django.conf import settings

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaLLM

logger = logging.getLogger(__name__)

# =====================================================
# GLOBAL CONFIG
# =====================================================
DATA_FILE = os.path.join(settings.BASE_DIR, "chatbot", "rag", "data", "overview.txt")
MODEL_NAME = "qwen2.5:1.5b"

_VECTOR_DB = None
_EMBEDDINGS = None
_LLM = None
_LAST_MTIME = 0

ROUND_ORDER_LIST = [
    "รอบที่ 1 Portfolio",
    "รอบที่ 1.2 Portfolio (MOU)",
    "รอบที่ 2 Quota",
    "รอบที่ 3 Admission",
    "รอบที่ 4 Direct Admission",
]

# คำใกล้เคียง (semantic เบา ๆ ไม่ fix แข็ง)
SYNONYM_MAP = {
    "รับกี่คน": ["จำนวนรับ", "รับ", "โควต้า"],
    "สมัคร": ["ยื่น", "ยื่นได้", "ยื่นได้ไหม"],
    "สาขา": ["หลักสูตร", "โปรแกรม"],
    "รอบ": ["portfolio", "quota", "admission"],
}

# =====================================================
# INIT MODELS & DB
# =====================================================
def get_embeddings():
    global _EMBEDDINGS
    if _EMBEDDINGS is None:
        _EMBEDDINGS = HuggingFaceEmbeddings(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
    return _EMBEDDINGS


def get_llm(fast=False):
    global _LLM
    if _LLM is None:
        _LLM = OllamaLLM(
            model=MODEL_NAME,
            temperature=0.3,
            num_ctx=2048 if fast else 4096,
            num_predict=256 if fast else 512
        )
    return _LLM


def load_vector_db():
    global _VECTOR_DB, _LAST_MTIME
    if not os.path.exists(DATA_FILE):
        return None

    current_mtime = os.path.getmtime(DATA_FILE)
    if _VECTOR_DB is None or current_mtime > _LAST_MTIME:
        reload_vector_db()
    return _VECTOR_DB


def reload_vector_db():
    global _VECTOR_DB, _LAST_MTIME
    try:
        embeddings = get_embeddings()
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            text = f.read()

        docs = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        ).create_documents([text])

        _VECTOR_DB = FAISS.from_documents(docs, embeddings)
        _LAST_MTIME = os.path.getmtime(DATA_FILE)
        return True
    except Exception as e:
        logger.error(e)
        return False


# =====================================================
# PROFILE & HELPERS
# =====================================================
def has_student_data(profile):
    return profile.get("gpax", 0) > 0


def expand_query(question):
    q = question.lower()
    expanded = [q]
    for k, syns in SYNONYM_MAP.items():
        if k in q:
            expanded.extend(syns)
    return " ".join(expanded)


def get_student_profile(history):
    profile = {
        "gpax": 0.0,
        "name": "น้อง",
        "math_credit": 0.0,
        "sci_credit": 0.0,
        "eng_credit": 0.0,
        "raw": ""
    }

    if not history:
        return profile

    for msg in reversed(history):
        if msg.get("role") == "system" and "[DATA_START]" in msg.get("content", ""):
            c = msg["content"]

            def ext(r):
                m = re.search(r, c)
                return float(m.group(1)) if m else 0.0

            profile.update({
                "gpax": ext(r"GPAX:\s*([\d\.]+)"),
                "math_credit": ext(r"MATH_CREDIT:\s*([\d\.]+)"),
                "sci_credit": ext(r"SCI_CREDIT:\s*([\d\.]+)"),
                "eng_credit": ext(r"ENG_CREDIT:\s*([\d\.]+)"),
                "name": re.search(r"ชื่อ:\s*([^\s]+)", c).group(1) if re.search(r"ชื่อ:\s*([^\s]+)", c) else "น้อง",
                "raw": c
            })
            break

    return profile


def format_card_pretty(text, profile):
    prog = re.search(r"หลักสูตร:\s*(.+)", text)
    if not prog:
        return None, False, ""

    p_name = prog.group(1).strip()

    m_gpa = re.search(r"GPAX ขั้นต่ำ:\s*([\d\.]+)", text)
    gpa_req = float(m_gpa.group(1)) if m_gpa else 0.0

    # 🔥 สำคัญ: ถ้าไม่มีข้อมูลนักเรียน → ไม่ filter GPAX
    if has_student_data(profile) and profile["gpax"] < gpa_req:
        return None, False, ""

    code = re.search(r"รหัสสาขา:\s*(\w+)", text)
    seats = re.search(r"จำนวนรับ:\s*(\d+)", text)

    card = (
        f"🎓 **{p_name}**\n"
        f"🆔 รหัส: `{code.group(1) if code else '-'}` | "
        f"👥 รับ: **{seats.group(1) if seats else '-'}** คน\n"
        f"⭐ GPAX ขั้นต่ำ: `{gpa_req}`"
    )

    return card, True, p_name


# =====================================================
# MAIN
# =====================================================
def ask_balanced(question: str, history: list = None) -> str:
    db = load_vector_db()
    if not db:
        return "⚠️ ระบบยังไม่พร้อมใช้งาน"

    profile = get_student_profile(history)
    search_q = expand_query(question)

    # 🔥 ไม่มีข้อมูล → ลด k เพื่อความเร็ว
    k = 8 if not has_student_data(profile) else 25
    docs = db.similarity_search(search_q, k=k)

    grouped = {r: [] for r in ROUND_ORDER_LIST}
    seen_cards = set()
    unique_majors = set()
    context_buffer = ""

    for d in docs:
        content = d.page_content
        context_buffer += content + "\n"

        found_round = None
        for r in ROUND_ORDER_LIST:
            if r.split()[0] in content and r.split()[2] in content:
                found_round = r
                break

        if not found_round:
            continue

        card, ok, pname = format_card_pretty(content, profile)
        if ok and card and card not in seen_cards:
            seen_cards.add(card)
            grouped[found_round].append(card)
            unique_majors.add(pname)

    # ==========================
    # FAST PATH (ไม่ใช้ LLM)
    # ==========================
    if unique_majors:
        header = (
            f"✨ **สรุปข้อมูลที่พบ**\n"
            f"👤 ผู้สมัคร: {profile['name']}\n"
        )

        if has_student_data(profile):
            header += f"📊 GPAX: `{profile['gpax']}`\n"

        output = [header]

        for r in ROUND_ORDER_LIST:
            if grouped[r]:
                output.append(f"\n### 📍 {r}")
                output.append("\n\n".join(grouped[r]))

        return "\n".join(output).strip()

    # ==========================
    # LLM FALLBACK (จำเป็นจริง)
    # ==========================
    llm = get_llm(fast=True)
    prompt = f"""
คุณคือรุ่นพี่แนะแนวการศึกษาคณะวิทยาศาสตร์
ข้อมูลที่มีจากระเบียบการ:
{context_buffer[:1200]}

ตอบคำถามให้น้องอย่างสุภาพ เป็นกันเอง ถ้าไม่ชัดเจนให้สรุปตามข้อมูลที่มี
"""

    try:
        return llm.invoke(f"{prompt}\nคำถาม: {question}").strip()
    except:
        return "❌ ระบบขัดข้อง กรุณาลองใหม่อีกครั้ง"
