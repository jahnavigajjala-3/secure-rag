import logging
from typing import Any, Dict, List, Optional
import numpy as np
from sqlalchemy.orm import Session

from app.database.models import Document, Role, User, document_roles, user_roles
from app.vectorstore.store import get_collection

# Import local Hugging Face sentence-transformers model directly
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Re-use your project's embedding model instance
_embedder = SentenceTransformer("all-MiniLM-L6-v2")


def embed_text(text: str) -> List[float]:
    return _embedder.encode(text).tolist()


def get_user_accessible_document_ids(user: User, db: Session) -> List[str]:
    """
    Query PostgreSQL to find all document_ids the user has permission to read.
    Superusers or admins with the 'admin' role get access to all documents.
    """
    user_role_names = [r.name for r in user.roles]

    if "admin" in user_role_names:
        docs = db.query(Document.id).filter(Document.status != "FAILED").all()
        return [str(d[0]) for d in docs]

    doc_ids = (
        db.query(Document.id)
        .join(document_roles, Document.id == document_roles.c.document_id)
        .join(Role, Role.id == document_roles.c.role_id)
        .join(user_roles, user_roles.c.role_id == Role.id)
        .filter(user_roles.c.user_id == user.id)
        .filter(Document.status != "FAILED")
        .distinct()
        .all()
    )

    return [str(d[0]) for d in doc_ids]


def select_best_document_id(
    query: str,
    accessible_docs: List[Document],
) -> Optional[str]:
    """
    Semantically score the query against accessible documents by analyzing
    filename and title concepts to isolate the target document.
    """
    if not accessible_docs:
        return None

    if len(accessible_docs) == 1:
        return str(accessible_docs[0].id)

    query_vec = np.array(embed_text(query), dtype=np.float32)
    query_norm = np.linalg.norm(query_vec) + 1e-9

    best_doc_id = str(accessible_docs[0].id)
    best_score = -float("inf")

    for doc in accessible_docs:
        clean_name = (
            doc.filename.replace("_", " ")
            .replace("-", " ")
            .replace(".pdf", "")
            .replace(".docx", "")
            .replace(".txt", "")
        )
        doc_descriptor = f"Document titled: {clean_name}"

        doc_vec = np.array(embed_text(doc_descriptor), dtype=np.float32)
        doc_norm = np.linalg.norm(doc_vec) + 1e-9

        score = float(np.dot(query_vec, doc_vec) / (query_norm * doc_norm))

        if score > best_score:
            best_score = score
            best_doc_id = str(doc.id)

    logger.info(
        f"[ROUTER] Scoped query to document_id='{best_doc_id}' (similarity={best_score:.4f})"
    )
    return best_doc_id


def retrieve(
    query: str,
    top_k: int = 5,
    distance_threshold: Optional[float] = None,
    where: Optional[Dict[str, Any]] = None,
    collection_name: str = "chunks",
) -> List[Dict[str, Any]]:
    """
    Low-level vector similarity search against ChromaDB collection.
    """
    collection = get_collection(name=collection_name)
    query_vector = embed_text(query)

    query_args: Dict[str, Any] = {
        "query_embeddings": [query_vector],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"],
    }

    if where:
        query_args["where"] = where

    results = collection.query(**query_args)

    retrieved: List[Dict[str, Any]] = []

    if not results or not results.get("ids") or not results["ids"][0]:
        return retrieved

    ids = results["ids"][0]
    docs = results["documents"][0] if results.get("documents") else []
    metas = results["metadatas"][0] if results.get("metadatas") else []
    distances = results["distances"][0] if results.get("distances") else []

    for i in range(len(ids)):
        dist = distances[i] if i < len(distances) else 0.0

        if distance_threshold is not None and dist > distance_threshold:
            continue

        retrieved.append(
            {
                "chunk_id": ids[i],
                "text": docs[i] if i < len(docs) else "",
                "distance": dist,
                "metadata": metas[i] if i < len(metas) else {},
            }
        )

    return retrieved


def retrieve_for_user(
    query: str,
    user: User,
    db: Session,
    top_k: int = 5,
    distance_threshold: Optional[float] = None,
    document_id: Optional[str] = None,
    collection_name: str = "chunks",
) -> List[Dict[str, Any]]:
    """
    Security-enforced & Document-routed retrieval:
    1. Resolve accessible document IDs via PostgreSQL RBAC.
    2. If an explicit document_id is passed, verify authorization.
    3. If multiple documents exist, semantically route query to the single best document.
    4. Query ChromaDB filtered strictly to that document_id.
    """
    allowed_doc_ids = get_user_accessible_document_ids(user, db)
    if not allowed_doc_ids:
        return []

    if document_id:
        if str(document_id) not in allowed_doc_ids:
            logger.warning(
                f"[RBAC BLOCK] User {user.id} denied access to document {document_id}"
            )
            return []
        target_doc_id = str(document_id)

    elif len(allowed_doc_ids) == 1:
        target_doc_id = allowed_doc_ids[0]

    else:
        accessible_docs = (
            db.query(Document)
            .filter(Document.id.in_(allowed_doc_ids))
            .filter(Document.status != "FAILED")
            .all()
        )
        target_doc_id = select_best_document_id(query, accessible_docs)

    where_filter = {"document_id": target_doc_id}

    return retrieve(
        query=query,
        top_k=top_k,
        distance_threshold=distance_threshold,
        where=where_filter,
        collection_name=collection_name,
    )