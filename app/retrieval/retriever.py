from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database.models import User, Role, Document
from app.ingestion.embedder import embed_text
from app.vectorstore.store import query_chunks

def get_user_accessible_document_ids(user: User, db: Session) -> List[str]:
    """
    Query PostgreSQL database to resolve all document IDs accessible to the given user based on RBAC.
    - Admin users get access to all READY documents.
    - Standard users get access ONLY to READY documents where document_roles intersects user.roles.
    """
    if not user:
        return []

    # 1. Collect roles from both direct attribute and relationship
    role_names = []
    if hasattr(user, "role") and user.role:
        role_names.append(str(user.role).lower())
    
    user_roles = getattr(user, "roles", []) or []
    role_names.extend([r.name.lower() for r in user_roles if hasattr(r, "name")])
    role_ids = [r.id for r in user_roles if hasattr(r, "id")]

    # 2. Admin check
    if "admin" in role_names or "administrator" in role_names:
        docs = db.query(Document.id).filter(Document.status == "READY").all()
        return [str(d[0]) for d in docs]

    if not role_ids:
        return []

    # 3. Intersect document_roles with user roles
    docs = (
        db.query(Document.id)
        .join(Document.roles)
        .filter(
            Document.status == "READY",
            Role.id.in_(role_ids)
        )
        .distinct()
        .all()
    )
    return [str(d[0]) for d in docs]

def retrieve(
    query: str, 
    top_k: int = 5, 
    distance_threshold: Optional[float] = 1.2,
    where: Optional[Dict[str, Any]] = None,
    collection_name: str = "chunks"
) -> List[Dict[str, Any]]:
    """
    Embed user query, query ChromaDB for top_k similarity matches with optional metadata filter,
    and filter results by configurable distance threshold.
    """
    if not query or not query.strip():
        return []

    query_embedding = embed_text(query)
    results = query_chunks(
        query_embedding=query_embedding, 
        top_k=top_k, 
        where=where,
        collection_name=collection_name
    )
    
    if not results or not results.get("documents") or not results["documents"][0]:
        return []

    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    retrieved_chunks = []
    for chunk_id, text, meta, dist in zip(ids, documents, metadatas, distances):
        if distance_threshold is not None and dist > distance_threshold:
            continue
            
        retrieved_chunks.append({
            "chunk_id": chunk_id,
            "text": text,
            "distance": dist,
            "metadata": meta
        })
        
    return retrieved_chunks

def retrieve_for_user(
    query: str,
    user: User,
    db: Session,
    top_k: int = 5,
    distance_threshold: Optional[float] = 1.2,
    collection_name: str = "chunks"
) -> List[Dict[str, Any]]:
    allowed_doc_ids = get_user_accessible_document_ids(user, db)
    print(f"\n[DEBUG] user: {user.email}, role: {getattr(user, 'role', None)}, roles: {getattr(user, 'roles', None)}")
    print(f"[DEBUG] allowed_doc_ids: {allowed_doc_ids}")

    if not allowed_doc_ids:
        print("[DEBUG] Exiting: allowed_doc_ids is empty.")
        return []

    if len(allowed_doc_ids) == 1:
        where_filter = {"document_id": allowed_doc_ids[0]}
    else:
        where_filter = {"document_id": {"$in": allowed_doc_ids}}

    print(f"[DEBUG] where_filter: {where_filter}")

    results = retrieve(
        query=query,
        top_k=top_k,
        distance_threshold=distance_threshold,
        where=where_filter,
        collection_name=collection_name
    )
    print(f"[DEBUG] retrieved chunks count: {len(results)}\n")
    return results
