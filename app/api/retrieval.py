from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import User
from app.auth.dependencies import get_current_user
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse
from app.retrieval.retriever import retrieve_for_user

router = APIRouter(prefix="/api/retrieval", tags=["Authorized Retrieval"])

@router.post("/search", response_model=RetrievalResponse)
def search_authorized_chunks(
    payload: RetrievalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Perform RBAC-enforced authorized retrieval for the authenticated user.
    - Resolves accessible document IDs for current user from PostgreSQL.
    - Applies 'document_id' metadata filter to ChromaDB query.
    - Returns only chunks belonging to documents the user is authorized to access.
    """
    if not payload.query or not payload.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty."
        )

    chunks = retrieve_for_user(
        query=payload.query,
        user=current_user,
        db=db,
        top_k=payload.top_k or 5,
        distance_threshold=payload.distance_threshold or 1.2
    )

    return RetrievalResponse(
        query=payload.query,
        retrieved_chunks=chunks,
        count=len(chunks)
    )
