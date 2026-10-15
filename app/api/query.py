from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import User
from app.auth.dependencies import get_current_user
from app.schemas.query import QueryRequest, QueryResponse
from app.retrieval.retriever import retrieve_for_user
import re


def is_trivial_greeting(text: str) -> bool:
    """Return True for short greetings where retrieval is unnecessary."""
    if not text or not text.strip():
        return True
    s = text.strip().lower()
    # pure short greetings like 'hi', 'hello', 'hii', 'hey', or 'good morning'
    if len(s) <= 4 and re.match(r'^(hi|hey|hii|yo)$', s):
        return True
    if re.match(r'^(hello|good morning|good afternoon|good evening|hi there)[\.!?]?$', s):
        return True
    return False
from app.generation.generator import generate_answer_with_sources

router = APIRouter(prefix="/api/query", tags=["Secure RAG Query Engine"])
rag_router = APIRouter(prefix="/api/rag", tags=["Secure RAG Query Engine"])

@router.post("", response_model=QueryResponse)
@rag_router.post("/query", response_model=QueryResponse)
def execute_authorized_rag_query(
    payload: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Execute end-to-end authorized RAG query pipeline:
    1. Authenticate user identity via Bearer JWT.
    2. Resolve user accessible document IDs via PostgreSQL RBAC.
    3. Perform metadata-filtered vector retrieval in ChromaDB.
    4. Generate grounded LLM answer with source citations (or pre-LLM fallback if no access/context).
    """
    if not payload.query or not payload.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty."
        )

    # Short-circuit for trivial greetings / small chit-chat — no retrieval needed
    if is_trivial_greeting(payload.query):
        return QueryResponse(
            query=payload.query,
            answer="Hello! I can search your authorized documents. Ask me a question about your documents or upload files to get started.",
            sources=[],
            grounded=False,
            retrieved_chunk_count=0,
        )

    # 1. Authorized Vector Retrieval
    retrieved_chunks = retrieve_for_user(
        query=payload.query,
        user=current_user,
        db=db,
        top_k=payload.top_k or 5,
        distance_threshold=payload.distance_threshold or 1.2
    )

    # 2. Grounded Answer Generation & Citation Extraction
    rag_result = generate_answer_with_sources(
        query=payload.query,
        retrieved_chunks=retrieved_chunks
    )

    citations = []
    for source in rag_result["sources"]:
        citations.append({
            "document_id": source.get("document_id"),
            "document_name": source.get("document_name") or source.get("filename"),
            "filename": source.get("filename"),
            "page": source.get("page"),
            "chunk_index": source.get("chunk_index"),
            "chunk_id": source.get("chunk_id"),
            "relevance_score": source.get("relevance_score", 0.0),
        })

    return QueryResponse(
        query=payload.query,
        answer=rag_result["answer"],
        sources=citations,
        grounded=rag_result["grounded"],
        retrieved_chunk_count=len(retrieved_chunks)
    )
