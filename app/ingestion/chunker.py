import re
from typing import List, Dict, Any


def _coerce_metadata(metadata: Dict[str, Any], *, doc_id: str, source: str, filename: str, filepath: str, chunk_index: int, page_number: int) -> Dict[str, Any]:
    meta = {
        "document_id": str(doc_id),
        "filename": str(filename),
        "source": str(source),
        "chunk_index": int(chunk_index),
        "page": int(page_number),
        "page_number": int(page_number),
    }
    meta.update({k: v for k, v in metadata.items() if v is not None})
    meta["document_id"] = str(meta.get("document_id", doc_id))
    meta["filename"] = str(meta.get("filename", filename))
    meta["source"] = str(meta.get("source", source))
    meta["chunk_index"] = int(meta.get("chunk_index", chunk_index))
    meta["page"] = meta.get("page", meta.get("page_number", page_number))
    meta["page_number"] = meta.get("page_number", meta.get("page", page_number))
    meta["filepath"] = str(filepath)
    return meta


def chunk_text(text: str, chunk_size: int = 200, chunk_overlap: int = 50) -> List[str]:
    """
    Split natural-language content with paragraph-aware chunking while preserving deterministic output.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be less than chunk_size")

    normalized = re.sub(r"\s+", " ", text or "").strip()
    if not normalized:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n{2,}|(?<=[.!?])\s+", normalized) if p and p.strip()]
    if len(paragraphs) == 1:
        paragraphs = [normalized]

    chunks: List[str] = []
    buffer = ""
    for paragraph in paragraphs:
        candidate = paragraph if not buffer else f"{buffer} {paragraph}"
        if len(candidate) <= chunk_size:
            buffer = candidate
            continue
        if buffer:
            chunks.append(buffer.strip())
            buffer = paragraph
            continue
        # paragraph is too long, fall back to deterministic character slicing without splitting mid-word if possible
        start = 0
        while start < len(paragraph):
            end = min(len(paragraph), start + chunk_size)
            segment = paragraph[start:end].strip()
            if segment:
                chunks.append(segment)
            start = end - chunk_overlap if start + chunk_size < len(paragraph) else end
            if start <= 0:
                break

    if buffer:
        chunks.append(buffer.strip())

    if not chunks:
        fallback = []
        step = chunk_size - chunk_overlap
        for start in range(0, len(normalized), step):
            end = start + chunk_size
            segment = normalized[start:end].strip()
            if segment:
                fallback.append(segment)
            if start + step >= len(normalized):
                break
        return fallback

    return chunks


def chunk_document(doc: Dict[str, Any], chunk_size: int = 200, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
    """
    Split a single document into chunk objects with chunk_id, text, and rich metadata.
    Preserves page-level metadata if available.
    """
    doc_id = str(doc.get("doc_id", "unknown_doc"))
    source = str(doc.get("source", "unknown_source"))
    filepath = str(doc.get("filepath", ""))
    filename = str(doc.get("filename", source))
    pages = doc.get("pages", [])
    page_number = None

    chunk_records = []
    global_chunk_idx = 0

    if pages:
        for page_obj in pages:
            page_number = page_obj.get("page_number")
            page_text = page_obj.get("text", "")
            if not page_text:
                continue
            for text_chunk in chunk_text(page_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap):
                chunk_records.append({
                    "chunk_id": f"{doc_id}_chunk_{global_chunk_idx}",
                    "text": text_chunk,
                    "metadata": _coerce_metadata(
                        {},
                        doc_id=doc_id,
                        source=source,
                        filename=filename,
                        filepath=filepath,
                        chunk_index=global_chunk_idx,
                        page_number=int(page_number) if page_number is not None else 1,
                    )
                })
                global_chunk_idx += 1
    else:
        content = doc.get("content", "")
        if content:
            for text_chunk in chunk_text(content, chunk_size=chunk_size, chunk_overlap=chunk_overlap):
                chunk_records.append({
                    "chunk_id": f"{doc_id}_chunk_{global_chunk_idx}",
                    "text": text_chunk,
                    "metadata": _coerce_metadata(
                        {},
                        doc_id=doc_id,
                        source=source,
                        filename=filename,
                        filepath=filepath,
                        chunk_index=global_chunk_idx,
                        page_number=1,
                    )
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