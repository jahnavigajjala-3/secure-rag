import os
import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Union, Optional
from app.ingestion.cleaner import clean_text

def extract_pdf_pages(path: Path) -> List[Dict[str, Any]]:
    """Extract text page-by-page from a PDF file using pypdf."""
    import pypdf
    pages = []
    reader = pypdf.PdfReader(str(path))
    for idx, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        cleaned = clean_text(raw_text)
        if cleaned:
            pages.append({"page_number": idx, "text": cleaned})
    return pages

def extract_docx_text(path: Path) -> str:
    """Extract text from a DOCX file using python-docx."""
    import docx
    doc = docx.Document(str(path))
    paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
    return "\n\n".join(paragraphs)

def load_document(file_path: Union[str, Path], doc_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Load a single document file (PDF, TXT, DOCX, MD, CSV, JSON).
    
    Returns:
        Dict containing doc_id, content, source filename, filepath, and pages list.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Document file not found: {file_path}")
    
    ext = path.suffix.lower()
    pages: List[Dict[str, Any]] = []
    full_text = ""

    if ext == ".pdf":
        try:
            pages = extract_pdf_pages(path)
            full_text = "\n\n".join([p["text"] for p in pages])
        except Exception:
            with path.open("r", encoding="utf-8", errors="ignore") as f:
                full_text = clean_text(f.read())
            if full_text:
                pages = [{"page_number": 1, "text": full_text}]
    elif ext in {".docx", ".doc"}:
        full_text = clean_text(extract_docx_text(path))
        if full_text:
            pages = [{"page_number": 1, "text": full_text}]
    elif ext in {".csv"}:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f)
            rows = [" , ".join(row) for row in reader if row]
            full_text = clean_text("\n".join(rows))
            if full_text:
                pages = [{"page_number": 1, "text": full_text}]
    elif ext in {".json"}:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            try:
                data = json.load(f)
                full_text = clean_text(json.dumps(data, indent=2))
            except Exception:
                f.seek(0)
                full_text = clean_text(f.read())
            if full_text:
                pages = [{"page_number": 1, "text": full_text}]
    else:
        # Fallback for plain text, markdown, etc.
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            full_text = clean_text(f.read())
        if full_text:
            pages = [{"page_number": 1, "text": full_text}]
            
    final_doc_id = str(doc_id) if doc_id else path.stem

    return {
        "doc_id": final_doc_id,
        "content": full_text,
        "source": path.name,
        "filepath": str(path.resolve()),
        "pages": pages
    }

def load_documents_from_directory(dir_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """
    Load all supported text/pdf/docx documents from a directory.
    """
    path = Path(dir_path)
    if not path.is_dir():
        raise NotADirectoryError(f"Directory not found: {dir_path}")
    
    documents = []
    for file_path in sorted(path.glob("*")):
        if file_path.is_file() and not file_path.name.startswith("."):
            try:
                doc = load_document(file_path)
                if doc["content"]:
                    documents.append(doc)
            except Exception as e:
                print(f"Warning: Failed to load {file_path}: {e}")
    return documents
