import os
import sys
import tempfile
import uuid
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.database import init_db, SessionLocal
from app.database.models import Document, Role
from app.ingestion.cleaner import clean_text
from app.ingestion.loader import load_document
from app.ingestion.chunker import chunk_document
from app.ingestion.embedder import embed_texts, embed_text
from app.ingestion.pipeline import ingest_document_by_id
from app.vectorstore.store import get_collection, query_chunks
from app.main import ingest_pipeline, run_naive_rag

def test_text_cleaner():
    raw_dirty = "Header \x00 Text\r\n\r\nLine  with   spaces\n\n\n\nDouble line break."
    cleaned = clean_text(raw_dirty)
    assert "\x00" not in cleaned
    assert "\r" not in cleaned
    assert "Line with spaces" in cleaned
    assert "\n\n\n" not in cleaned
    print("✓ test_text_cleaner passed")

def test_pdf_extraction():
    import pypdf
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_path = Path(tmp.name)
    try:
        writer = pypdf.PdfWriter()
        page1 = writer.add_blank_page(width=612, height=792)
        # Write some text (pypdf stream writing or minimal PDF structure)
        writer.write(str(pdf_path))
        
        doc_data = load_document(pdf_path)
        assert doc_data["source"] == pdf_path.name
        assert "pages" in doc_data
        print("✓ test_pdf_extraction passed")
    finally:
        if pdf_path.exists():
            pdf_path.unlink()

def test_docx_extraction():
    import docx
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        docx_path = Path(tmp.name)
    try:
        doc = docx.Document()
        doc.add_heading("Ingestion Pipeline Audit", level=1)
        doc.add_paragraph("This is a test paragraph for DOCX parsing verification.")
        doc.save(str(docx_path))

        doc_data = load_document(docx_path)
        assert "Ingestion Pipeline Audit" in doc_data["content"]
        assert "test paragraph for DOCX" in doc_data["content"]
        assert len(doc_data["pages"]) >= 1
        print("✓ test_docx_extraction passed")
    finally:
        if docx_path.exists():
            docx_path.unlink()

def test_chunker_metadata():
    doc_sample = {
        "doc_id": "test_doc_123",
        "source": "financial_report.pdf",
        "filepath": "/data/financial_report.pdf",
        "pages": [
            {"page_number": 1, "text": "Page 1 Executive Summary. Python is an interpreted programming language."},
            {"page_number": 2, "text": "Page 2 Financial Results. Q3 revenue grew by 25% year over year."}
        ]
    }
    chunks = chunk_document(doc_sample, chunk_size=100, chunk_overlap=20)
    assert len(chunks) >= 2
    for idx, c in enumerate(chunks):
        assert c["chunk_id"] == f"test_doc_123_chunk_{idx}"
        assert c["metadata"]["document_id"] == "test_doc_123"
        assert c["metadata"]["filename"] == "financial_report.pdf"
        assert "page" in c["metadata"]
        assert "chunk_index" in c["metadata"]
    print("✓ test_chunker_metadata passed")

def test_embedding_generation():
    text = "Secure RAG vector ingestion unit test."
    vec = embed_text(text)
    assert isinstance(vec, list)
    assert len(vec) == 384
    
    vecs = embed_texts([text, "Second sentence for batch embedding."])
    assert len(vecs) == 2
    assert len(vecs[0]) == 384
    print("✓ test_embedding_generation passed")

def test_status_transitions_and_indexing():
    init_db()
    db = SessionLocal()
    try:
        # Create temp TXT file
        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False, encoding="utf-8") as tmp:
            tmp.write("Confidential Security Policy: All API keys must be rotated every 90 days.")
            tmp_path = Path(tmp.name)

        doc_record = Document(
            filename=tmp_path.name,
            file_path=str(tmp_path.resolve()),
            file_size=os.path.getsize(tmp_path),
            chunk_count=0,
            status="UPLOADED"
        )
        db.add(doc_record)
        db.commit()
        db.refresh(doc_record)

        assert doc_record.status == "UPLOADED"

        # Execute Ingestion Pipeline
        ingested_doc = ingest_document_by_id(doc_record.id, db)
        assert ingested_doc.status == "READY"
        assert ingested_doc.chunk_count > 0

        # Query ChromaDB to verify chunk metadata and vector indexing
        coll = get_collection()
        chroma_res = coll.get(where={"document_id": str(doc_record.id)})
        assert len(chroma_res["ids"]) > 0
        assert chroma_res["metadatas"][0]["document_id"] == str(doc_record.id)
        assert chroma_res["metadatas"][0]["filename"] == tmp_path.name

        print("✓ test_status_transitions_and_indexing passed")

    finally:
        db.close()
        if tmp_path.exists():
            tmp_path.unlink()

def test_failed_status_transition():
    init_db()
    db = SessionLocal()
    try:
        non_existent_path = f"/tmp/non_existent_doc_{uuid.uuid4().hex}.txt"
        doc_record = Document(
            filename="missing_doc.txt",
            file_path=non_existent_path,
            file_size=100,
            chunk_count=0,
            status="UPLOADED"
        )
        db.add(doc_record)
        db.commit()
        db.refresh(doc_record)

        try:
            ingest_document_by_id(doc_record.id, db)
        except Exception:
            pass

        db.refresh(doc_record)
        assert doc_record.status == "FAILED"
        print("✓ test_failed_status_transition passed")
    finally:
        db.close()

def test_end_to_end_naive_rag():
    print("\n--------------------------------------------------")
    print("RUNNING END-TO-END NAIVE RAG PIPELINE VERIFICATION")
    print("--------------------------------------------------")
    
    chunk_count = ingest_pipeline()
    assert chunk_count > 0, f"Expected > 0 chunks, got {chunk_count}"
    
    relevant_query = "What is Python used for?"
    result_rel = run_naive_rag(relevant_query, top_k=3, distance_threshold=1.2)
    assert len(result_rel["retrieved_chunks"]) > 0, "Relevant query should return retrieved chunks."
    
    print("✓ test_end_to_end_naive_rag passed")

def run_all_milestone3_tests():
    test_text_cleaner()
    test_pdf_extraction()
    test_docx_extraction()
    test_chunker_metadata()
    test_embedding_generation()
    test_status_transitions_and_indexing()
    test_failed_status_transition()
    test_end_to_end_naive_rag()
    print("\n==================================================")
    print("ALL MILESTONE 3 INGESTION PIPELINE TESTS PASSED SUCCESSFULLY!")
    print("==================================================\n")

if __name__ == "__main__":
    run_all_milestone3_tests()
