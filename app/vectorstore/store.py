import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database.database import SessionLocal
from app.database.models import DocumentChunk

logger = logging.getLogger(__name__)

def store_chunks(db: Session, chunks_data: List[Dict[str, Any]]):
    """Store chunk records and their embeddings into Supabase pgvector."""
    for item in chunks_data:
        chunk = DocumentChunk(
            id=item["id"],
            document_id=item["document_id"],
            content=item["content"],
            chunk_index=item["chunk_index"],
            embedding=item["embedding"]
        )
        db.merge(chunk)  # Upsert behavior
    db.commit()


def add_chunks(document_id: str, chunks: List[str], embeddings: List[List[float]], chunk_ids: Optional[List[str]] = None) -> None:
    """
    Backward-compatible wrapper for pipeline ingestion.
    """
    db: Session = SessionLocal()
    try:
        chunks_data = []
        for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = chunk_ids[idx] if chunk_ids and idx < len(chunk_ids) else None
            item = {
                "id": chunk_id,
                "document_id": document_id,
                "content": chunk_text,
                "chunk_index": idx,
                "embedding": embedding
            }
            chunks_data.append(item)
        
        store_chunks(db, chunks_data)
        logger.info(f"[VECTORSTORE] Successfully inserted {len(chunks)} chunks for document_id={document_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"[VECTORSTORE ERROR] Failed to insert chunks for document {document_id}: {e}")
        raise
    finally:
        db.close()


def query_similar_chunks(
    db: Session, 
    query_embedding: List[float], 
    top_k: int = 5, 
    authorized_doc_ids: List[str] = None
):
    """Query pgvector for top-k similar chunks filtered by authorized document_ids."""
    stmt = select(DocumentChunk)
    
    if authorized_doc_ids is not None:
        if not authorized_doc_ids:
            return []
        stmt = stmt.where(DocumentChunk.document_id.in_(authorized_doc_ids))
    
    stmt = stmt.order_by(DocumentChunk.embedding.cosine_distance(query_embedding)).limit(top_k)
    
    results = db.scalars(stmt).all()
    return results


def delete_chunks_by_document_id(document_id: str):
    """Delete all chunks belonging to a document_id."""
    db: Session = SessionLocal()
    try:
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
        db.commit()
        logger.info(f"[VECTORSTORE] Deleted all chunks for document_id={document_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"[VECTORSTORE ERROR] Failed to delete chunks for document {document_id}: {e}")
        raise
    finally:
        db.close()
def reset_collection():
    """
    Clear all document chunks from PostgreSQL (equivalent to resetting the vector collection).
    """
    db: Session = SessionLocal()
    try:
        db.query(DocumentChunk).delete()
        db.commit()
        logger.info("[VECTORSTORE] Reset vector store: all chunks deleted.")
    except Exception as e:
        db.rollback()
        logger.error(f"[VECTORSTORE ERROR] Failed to reset vector store: {e}")
        raise
    finally:
        db.close()