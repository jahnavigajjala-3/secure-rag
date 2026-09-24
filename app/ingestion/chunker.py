from typing import List, Dict, Any

def chunk_text(text: str, chunk_size: int = 200, chunk_overlap: int = 50) -> List[str]:
    """
    Split raw text into fixed-size character chunks with optional overlap.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be less than chunk_size")
    
    if not text:
        return []

    step = chunk_size - chunk_overlap
    chunks = []
    for start in range(0, len(text), step):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if start + step >= len(text):
            break
    return chunks


def chunk_document(doc: Dict[str, Any], chunk_size: int = 200, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
    """
    Split a single document into chunk objects with chunk_id, text, and rich metadata.
    Preserves page-level metadata if available.
    """
    doc_id = str(doc.get("doc_id", "unknown_doc"))
    source = str(doc.get("source", "unknown_source"))
    filepath = str(doc.get("filepath", ""))
    pages = doc.get("pages", [])

    chunk_records = []
    global_chunk_idx = 0

    if pages:
        for page_obj in pages:
            page_num = page_obj.get("page_number", 1)
            page_text = page_obj.get("text", "")
            if not page_text:
                continue
            text_chunks = chunk_text(page_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            for text_chunk in text_chunks:
                chunk_records.append({
                    "chunk_id": f"{doc_id}_chunk_{global_chunk_idx}",
                    "text": text_chunk,
                    "metadata": {
                        "document_id": doc_id,
                        "filename": source,
                        "source": source,
                        "filepath": filepath,
                        "page": page_num,
                        "chunk_index": global_chunk_idx
                    }
                })
                global_chunk_idx += 1
    else:
        content = doc.get("content", "")
        if content:
            text_chunks = chunk_text(content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            for text_chunk in text_chunks:
                chunk_records.append({
                    "chunk_id": f"{doc_id}_chunk_{global_chunk_idx}",
                    "text": text_chunk,
                    "metadata": {
                        "document_id": doc_id,
                        "filename": source,
                        "source": source,
                        "filepath": filepath,
                        "page": 1,
                        "chunk_index": global_chunk_idx
                    }
                })
                global_chunk_idx += 1

    return chunk_records


def chunk_documents(documents: List[Dict[str, Any]], chunk_size: int = 200, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
    """
    Split a list of document dicts into chunk objects.
    """
    all_chunks = []
    for doc in documents:
        all_chunks.extend(chunk_document(doc, chunk_size=chunk_size, chunk_overlap=chunk_overlap))
    return all_chunks