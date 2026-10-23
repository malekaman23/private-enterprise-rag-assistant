"""
vector_store.py
----------------
Yeh module document chunks ko "embeddings" (numbers ki form) mein
convert karke ChromaDB naam ke local database mein store karta hai.

Jab user koi sawal puchta hai, uska embedding banake yaha se
sabse "milte-julte" (relevant) chunks dhundh liye jaate hain -
isi ko "similarity search" bolte hain.
"""

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from functools import lru_cache

import config
from tenant_utils import DEFAULT_TENANT_ID, safe_scope
from access_policy import allowed_required_roles, accessible_departments, validate_required_role


@lru_cache(maxsize=1)
def get_embedding_model():
    """Free, local embedding model load karta hai (internet sirf pehli baar chahiye)."""
    return HuggingFaceEmbeddings(model_name=config.EMBEDDING_MODEL)


def _store_path(tenant_id: str) -> str:
    # Preserve the original personal store; new tenants are isolated on disk.
    if tenant_id == DEFAULT_TENANT_ID:
        return config.VECTORSTORE_DIR
    return f"{config.VECTORSTORE_DIR}/tenants/{safe_scope(tenant_id, DEFAULT_TENANT_ID)}"


def build_vectorstore(chunks, category: str = "General", tenant_id: str = DEFAULT_TENANT_ID,
                      owner_user_id: str = "", access_scope: str = "tenant",
                      department_id: str = "", required_role: str = "shared"):
    """
    Naye document chunks se vector database banata hai.
    Har chunk ko 'category' metadata tag ki jaati hai, taaki baad mein
    category ke hisaab se filter karke search kiya ja sake.
    """
    required_role = validate_required_role(required_role)
    for chunk in chunks:
        chunk.metadata["category"] = category
        chunk.metadata["tenant_id"] = tenant_id
        chunk.metadata["access_scope"] = access_scope
        chunk.metadata["department_id"] = department_id
        chunk.metadata["required_role"] = required_role
        if owner_user_id:
            chunk.metadata["owner_user_id"] = owner_user_id

    embeddings = get_embedding_model()
    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=_store_path(tenant_id),
    )
    print(f"Vectorstore ban gaya: {config.VECTORSTORE_DIR} (category: {category})")
    return vectordb


def load_vectorstore(tenant_id: str = DEFAULT_TENANT_ID):
    """Pehle se bane hue vectorstore ko load karta hai (dubara process nahi karna padta)."""
    embeddings = get_embedding_model()
    vectordb = Chroma(
        persist_directory=_store_path(tenant_id),
        embedding_function=embeddings,
    )
    return vectordb


def _access_filter(tenant_id: str, user_id: str, departments: tuple[str, ...] = (), roles: tuple[str, ...] = ()):
    if tenant_id == DEFAULT_TENANT_ID:
        return None
    clauses = [{"$and": [{"access_scope": "user"}, {"owner_user_id": user_id}]}]
    allowed_roles = allowed_required_roles(roles, departments)
    allowed_departments = accessible_departments(roles, departments)
    for required_role in allowed_roles:
        clauses.append({"$and": [
            {"access_scope": "tenant"}, {"required_role": required_role},
            {"department_id": ""},
        ]})
        if "*" in allowed_departments:
            clauses.append({"$and": [
                {"access_scope": "tenant"}, {"required_role": required_role},
            ]})
            continue
        for department in allowed_departments:
            clauses.append({"$and": [
                {"access_scope": "tenant"}, {"required_role": required_role},
                {"department_id": department},
            ]})
    return {"$or": clauses}


def search_documents(query: str, k: int = None, category: str = None,
                     tenant_id: str = DEFAULT_TENANT_ID, user_id: str = "",
                     departments: tuple[str, ...] = (), roles: tuple[str, ...] = ()):
    """
    User ke query se sabse relevant chunks dhundhta hai.
    Agar 'category' diya gaya hai, to sirf usi category ke documents
    mein search hoga - baaki sab ignore honge.
    """
    k = k or config.TOP_K_RESULTS
    vectordb = load_vectorstore(tenant_id)

    # The legacy personal store predates ACL metadata and remains available to
    # the single local personal profile. New tenant stores always use this ACL.
    access_filter = _access_filter(tenant_id, user_id, departments, roles)
    if category and category != "All":
        filter_value = {"category": category}
        if access_filter:
            filter_value = {"$and": [filter_value, access_filter]}
        results = vectordb.similarity_search(query, k=k, filter=filter_value)
    elif access_filter:
        results = vectordb.similarity_search(query, k=k, filter=access_filter)
    else:
        results = vectordb.similarity_search(query, k=k)

    return results


def get_all_categories(tenant_id: str = DEFAULT_TENANT_ID, user_id: str = "",
                       departments: tuple[str, ...] = (), roles: tuple[str, ...] = ()):
    """Ab tak jitni bhi categories mein documents upload hue hain, unki list deta hai."""
    try:
        vectordb = load_vectorstore(tenant_id)
        access_filter = _access_filter(tenant_id, user_id, departments, roles)
        if access_filter:
            all_data = vectordb.get(where=access_filter)
        else:
            all_data = vectordb.get()
        categories = set()
        for metadata in all_data.get("metadatas", []):
            if metadata and "category" in metadata:
                categories.add(metadata["category"])
        return sorted(categories)
    except Exception:
        return []


def list_documents(tenant_id: str = DEFAULT_TENANT_ID, user_id: str = "",
                   departments: tuple[str, ...] = (), roles: tuple[str, ...] = ()):
    """
    Ab tak upload hui saari files ki list deta hai, har ek ki category
    aur kitne chunks bane the, uske saath. Return: list of dicts.
    """
    try:
        vectordb = load_vectorstore(tenant_id)
        access_filter = _access_filter(tenant_id, user_id, departments, roles)
        if access_filter:
            all_data = vectordb.get(where=access_filter)
        else:
            all_data = vectordb.get()
        files = {}
        for metadata in all_data.get("metadatas", []):
            if not metadata:
                continue
            fname = metadata.get("source_file", "unknown")
            category = metadata.get("category", "General")
            key = (fname, category)
            files[key] = files.get(key, 0) + 1

        return [
            {"filename": fname, "category": category, "chunks": count}
            for (fname, category), count in sorted(files.items())
        ]
    except Exception:
        return []


def delete_document(filename: str, category: str = None, tenant_id: str = DEFAULT_TENANT_ID):
    """
    Ek document ke saare chunks vectorstore se delete karta hai.
    Agar category bhi di gayi hai, to sirf usi category wale filename
    ke chunks delete honge (taaki same filename alag category mein ho
    to galti se dono na mit jayein).
    """
    vectordb = load_vectorstore(tenant_id)
    where_filter = {"source_file": filename}
    if category:
        where_filter = {"$and": [{"source_file": filename}, {"category": category}]}

    matching = vectordb.get(where=where_filter)
    ids_to_delete = matching.get("ids", [])
    if ids_to_delete:
        vectordb.delete(ids=ids_to_delete)
    return len(ids_to_delete)


def delete_documents(filenames: list[str], tenant_id: str = DEFAULT_TENANT_ID) -> int:
    """Delete several source files with one vector-store/model load."""
    if not filenames:
        return 0
    vectordb = load_vectorstore(tenant_id)
    ids_to_delete = []
    for filename in filenames:
        matching = vectordb.get(where={"source_file": filename})
        ids_to_delete.extend(matching.get("ids", []))
    if ids_to_delete:
        vectordb.delete(ids=ids_to_delete)
    return len(ids_to_delete)


def delete_category(category: str, tenant_id: str = DEFAULT_TENANT_ID) -> int:
    """Remove all indexed chunks in one category without touching source files."""
    vectordb = load_vectorstore(tenant_id)
    matching = vectordb.get(where={"category": category})
    ids_to_delete = matching.get("ids", [])
    if ids_to_delete:
        vectordb.delete(ids=ids_to_delete)
    return len(ids_to_delete)
