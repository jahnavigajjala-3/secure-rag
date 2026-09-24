import io
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.database import init_db, SessionLocal
from app.database.seed import seed_dev_users, DEV_ADMIN_EMAIL, DEV_ADMIN_PASSWORD
from app.database.models import Document, Role, User
from app.ingestion.loader import load_document, clean_text
from app.ingestion.chunker import chunk_document, chunk_text
from app.ingestion.embedder import embed_texts, embed_query
from app.ingestion.pipeline import ingest_document_by_id
from app.vectorstore.store import query_chunks, delete_chunks_by_document_id

def test_ingestion_pipeline():
    init_db()
    seed_dev_users()
    db = SessionLocal()

    # 1. Test Text Cleaning & Extraction
    raw_text = "  Confidential   Corporate   Policy \x00\x07  \n\n  Section 1: Security.  "
    cleaned = clean_text(raw_text)
    assert "Confidential Corporate Policy" in cleaned
    assert "Section 1: Security." in cleaned

    # 2. Test Deterministic Chunking & Metadata Preservation
    doc_dict = {
        "doc_id": "test_doc_001",
        "source": "security_policy.pdf",
        "filepath": "/tmp/security_policy.pdf",
        "pages": [
            {"page_number": 1, "text": "This is page 1 content covering data protection regulations."},
            {"page_number": 2, "text": "This is page 2 content covering password policies and encryption."}
        ]
    }
    chunks = chunk_document(doc_dict, chunk_size=100, chunk_overlap=20)
    assert len(chunks) >= 2
    assert chunks[0]["metadata"]["document_id"] == "test_doc_001"
    assert chunks[0]["metadata"]["filename"] == "security_policy.pdf"
    assert chunks[0]["metadata"]["page"] in [1, 2]

    # 3. Test Embedding Generation
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)
    assert len(embeddings) == len(texts)
    assert len(embeddings[0]) == 384  # MiniLM-L6-v2 vector dimension

    # 4. Test Full Pipeline Ingestion with Status Transitions
    # Create physical test file
    test_dir = Path(__file__).parent.parent / "data" / "documents"
    test_dir.mkdir(parents=True, exist_ok=True)
    file_path = test_dir / f"ingest_test_{uuid.uuid4().hex[:6]}.txt"
    file_path.write_text("SecureRAG automated pipeline test file. Python and FastAPI power the backend.", encoding="utf-8")

    admin_user = db.query(User).filter(User.email == DEV_ADMIN_EMAIL).first()
    admin_role = db.query(Role).filter(Role.name == "admin").first()

    new_doc = Document(
        filename=file_path.name,
        file_path=str(file_path.resolve()),
        file_size=file_path.stat().st_size,
        status="UPLOADED",
        uploaded_by_id=admin_user.id if admin_user else None
    )
    if admin_role:
        new_doc.roles.append(admin_role)
    db.add(new_doc)
    db.commit()
    db.refresh(new_doc)

    # Ingest document
    ingested_doc = ingest_document_by_id(new_doc.id, db)
    assert ingested_doc.status == "READY"
    assert ingested_doc.chunk_count > 0

    # Verify vector store search maps back to document_id
    q_vec = embed_query("FastAPI backend")
    vector_res = query_chunks(query_embedding=q_vec, top_k=3, where={"document_id": new_doc.id})
    assert len(vector_res.get("ids", [[]])[0]) > 0
    retrieved_meta = vector_res["metadatas"][0][0]
    assert retrieved_meta["document_id"] == new_doc.id

    # Clean up test file & vector chunks
    delete_chunks_by_document_id(new_doc.id)
    if file_path.exists():
        file_path.unlink()
    db.delete(new_doc)
    db.commit()
    db.close()

    print("ALL MILESTONE 3 INGESTION PIPELINE TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_ingestion_pipeline()
