"""
long_term_memory.py
--------------------
Yeh module "Long-Term Memory" implement karta hai - matlab assistant
sirf last few messages nahi, balki HAR purani baatcheet ko "meaning"
ke hisaab se yaad rakhta hai aur relevant hone par dhundh ke nikaal leta hai.

Kaise kaam karta hai:
1. Har message (user ka ho ya assistant ka) ko ek "embedding" (meaning ka
   numeric representation) mein convert karke ek alag ChromaDB collection
   mein store kar dete hain (documents wale collection se ALAG rakha hai,
   taaki dono mix na ho).
2. Jab naya sawal aata hai, uska embedding banake, purani saari memory mein
   se "sabse milte-julte" (relevant) purane messages dhundh liye jaate hain -
   fir wahi context LLM ko diya jaata hai.

Isse fayda: agar tumne 50 messages pehle kaha tha "mera birthday 15 August
hai", aur ab pucho "mera birthday kab hai", to short-term memory (sirf last
6 messages) isse miss kar deti, lekin long-term memory isse dhundh legi.
"""

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from datetime import datetime
import os
from functools import lru_cache

import config
from tenant_utils import DEFAULT_TENANT_ID, DEFAULT_USER_ID, safe_scope

LONG_TERM_MEMORY_DIR = "memory/long_term_vectorstore"


@lru_cache(maxsize=1)
def get_embedding_model():
    """Documents ke liye jo embedding model use hota hai, wahi yaha bhi use karenge."""
    return HuggingFaceEmbeddings(model_name=config.EMBEDDING_MODEL)


def get_memory_store(tenant_id: str = DEFAULT_TENANT_ID, user_id: str = DEFAULT_USER_ID):
    """Long-term memory ka apna alag ChromaDB collection load/banata hai."""
    if tenant_id == DEFAULT_TENANT_ID and user_id == DEFAULT_USER_ID:
        memory_dir = LONG_TERM_MEMORY_DIR
        collection_name = "long_term_memory"
    else:
        memory_dir = os.path.join(
            "memory", "tenants", safe_scope(tenant_id, DEFAULT_TENANT_ID),
            "users", safe_scope(user_id, DEFAULT_USER_ID), "long_term_vectorstore"
        )
        collection_name = "long_term_memory_" + safe_scope(user_id, DEFAULT_USER_ID)
    os.makedirs(memory_dir, exist_ok=True)
    embeddings = get_embedding_model()
    return Chroma(
        persist_directory=memory_dir,
        embedding_function=embeddings,
        collection_name=collection_name,
    )


def save_to_long_term_memory(role: str, message: str, tenant_id: str = DEFAULT_TENANT_ID, user_id: str = DEFAULT_USER_ID):
    """
    Ek message ko long-term memory mein save karta hai.
    role: "user" ya "assistant"
    message: actual text
    """
    if not message or not message.strip():
        return

    store = get_memory_store(tenant_id, user_id)
    doc = Document(
        page_content=message,
        metadata={
            "role": role,
            "timestamp": datetime.now().isoformat(),
        },
    )
    store.add_documents([doc])


def recall_relevant_memory(query: str, k: int = 4, min_relevance: float = 0.55,
                          tenant_id: str = DEFAULT_TENANT_ID, user_id: str = DEFAULT_USER_ID):
    """
    User ke naye sawal se related PURANI (kabhi bhi ki gayi) baatein dhundhta hai.
    Yeh recent history se ALAG hai - yeh "meaning se match" karta hai,
    chahe baat kitni bhi purani kyun na ho.

    'min_relevance' ek threshold hai (0 se 1) - sirf genuinely relevant
    memory include hogi. Chroma "nearest k" hamesha kuch na kuch return
    karta hai chahe woh actually related ho ya na ho, isliye threshold
    lagakar irrelevant/noise wali purani baatein filter out karte hain
    (especially chhote local models ko confuse hone se bachata hai).
    """
    try:
        store = get_memory_store(tenant_id, user_id)
        results = store.similarity_search_with_relevance_scores(query, k=k)
        if not results:
            return ""

        formatted = []
        for r, score in results:
            if score < min_relevance:
                continue  # itna relevant nahi, skip karo (noise mat banao)
            role = r.metadata.get("role", "unknown")
            timestamp = r.metadata.get("timestamp", "")
            formatted.append(f"[{role} - {timestamp[:10]}]: {r.page_content}")

        return "\n".join(formatted)
    except Exception:
        # Agar memory store abhi khaali hai (koi purani baat nahi), error na aaye
        return ""


def clear_long_term_memory():
    """Poori long-term memory delete kar deta hai (fresh start ke liye)."""
    import shutil
    if os.path.exists(LONG_TERM_MEMORY_DIR):
        shutil.rmtree(LONG_TERM_MEMORY_DIR)
