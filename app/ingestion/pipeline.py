import logging
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.database.models import Document
from app.ingestion.loader import load_document
from app.ingestion.chunker import chunk_document
from app.ingestion.embedder import embed_texts
from app.vectorstore.store import add_chunks, delete_chunks_by_document_id

logger = logging.getLogger(__name__)

def ingest_document_by_id(
    doc_id: str, 
    db: Session, 
    chunk_size: int = 200, 
    chunk_overlap: int = 50
) -> Document:
    """
    Ingest a document registered in PostgreSQL by its ID with explicit status transitions:
    UPLOADED -> PROCESSING -> READY (or FAILED on error).
    """
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise ValueError(f"Document with id '{doc_id}' not found in database.")

    # 1. Transition to PROCESSING
    doc.status = "PROCESSING"
    db.commit()
    db.refresh(doc)

    try:
        file_path = Path(doc.file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Physical file missing at path: {doc.file_path}")

        # 2. Load & parse document
        raw_doc = load_document(file_path, doc_id=doc.id)
        
        # Override source filename with DB filename if available
        if doc.filename:
            raw_doc["source"] = doc.filename

        # 3. Chunk document with metadata
        chunks = chunk_document(raw_doc, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        if chunks:
            # If reprocessing, remove any existing vectors for this document first
            try:
                delete_chunks_by_document_id(doc.id)
            except Exception:
                # deletion failures should not block ingestion; log and continue
                logger.warning(f"Failed to remove existing chunks for document {doc.id} before re-indexing.")
            # 4. Generate embeddings
            texts = [c["text"] for c in chunks]
            embeddings = embed_texts(texts)

            # 5. Insert into ChromaDB (upsert with stable chunk IDs)
            add_chunks(chunks, embeddings)

            # Only mark chunk count after successful upsert
            doc.chunk_count = len(chunks)
        else:
            doc.chunk_count = 0

        # 6. Transition to READY
        doc.status = "READY"
        db.commit()
        db.refresh(doc)
        logger.info(f"Successfully ingested document '{doc.filename}' (ID: {doc.id}) - status: READY, chunks: {doc.chunk_count}")
        return doc

    except Exception as e:
        logger.error(f"Failed to ingest document '{doc.filename}' (ID: {doc.id}): {e}")
        doc.status = "FAILED"
        doc.error_message = "Document processing failed. Please contact an administrator for details."
        db.commit()
        db.refresh(doc)
        raise e
