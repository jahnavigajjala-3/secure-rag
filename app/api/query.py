from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import User
from app.auth.dependencies import get_current_user
from app.schemas.query import QueryRequest, QueryResponse
from app.retrieval.retriever import retrieve_for_user
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

    return QueryResponse(
        query=payload.query,
        answer=rag_result["answer"],
        sources=rag_result["sources"],
        grounded=rag_result["grounded"],
        retrieved_chunk_count=len(retrieved_chunks)
    )
