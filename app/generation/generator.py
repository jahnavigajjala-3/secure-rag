import os
import re
import time
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from google import genai

load_dotenv()

_client = None

def get_genai_client() -> Optional[genai.Client]:
    """
    Initialize and return google-genai Client if GEMINI_API_KEY is available.
    """
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "YOUR_GEMINI_API_KEY":
            return None
        try:
            _client = genai.Client(api_key=api_key)
        except Exception as e:
            print(f"Warning: Failed to initialize Gemini client: {e}")
            return None
    return _client


def generate_answer(query: str, context_chunks: List[str]) -> str:
    """
    Generate grounded answer using Gemini if configured; otherwise synthesize from retrieved context.
    """
    if not context_chunks:
        return "I cannot answer this question based on your accessible documents because no relevant information was found."

    context_text = "\n\n".join(context_chunks)

    prompt = f"""You are a helpful and strict corporate QA assistant. Answer the user's question using ONLY the provided context below.

Rules:
1. Answer using ONLY the provided context.
2. If the context does not contain enough information to answer the question, state that the answer cannot be found in the provided documents.
3. Do not invent information or extrapolate beyond the provided text.
4. Keep the answer clear, accurate, and concise.

Context:
{context_text}

Question:
{query}
"""

    client = get_genai_client()
    if client:
        max_retries = 3
        backoff = 1.0
        for attempt in range(1, max_retries + 1):
            try:
                interaction = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=prompt,
                )
                answer = getattr(interaction, "text", None) or str(interaction)
                return answer
            except Exception as e:
                # transient failures: retry with exponential backoff
                if attempt < max_retries:
                    print(f"Gemini call failed (attempt {attempt}/{max_retries}): {e}. Retrying in {backoff}s...")
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                print(f"Warning: Gemini API call failed ({e}). Falling back to grounded context synthesis.")

    # Clean fallback: don't dump raw chunk text to the user. Show a clear message
    # so the UI doesn't display confusing retrieved content as the "answer".
    return (
        "I'm sorry, the AI model is temporarily unavailable. "
        "Please try again in a moment. Your documents were retrieved successfully — "
        f"{len(context_chunks)} relevant chunk(s) were found."
    )


def generate_answer_with_sources(query: str, retrieved_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate answer with detailed source citations and pre-LLM short-circuit fallback for empty context.
    """
    if not retrieved_chunks:
        return {
            "answer": "I couldn't find enough information in your authorized documents to answer that.",
            "sources": [],
            "grounded": False
        }

    context_blocks = []
    sources_map = {}

    for idx, chunk in enumerate(retrieved_chunks, start=1):
        text = chunk.get("text", "").strip()
        meta = chunk.get("metadata", {})
        doc_id = meta.get("document_id", "unknown_doc")
        filename = meta.get("filename") or meta.get("document_name") or meta.get("source") or "unknown_file"
        page = meta.get("page", meta.get("page_number"))
        chunk_index = meta.get("chunk_index", 0)
        chunk_id = chunk.get("chunk_id", f"{doc_id}:{idx}")
        dist = float(chunk.get("distance", 0.0))
        rel_score = round(max(0.0, min(1.0, 1.0 - dist)), 4)

        context_blocks.append(f"[Document: {filename} | Page: {page if page is not None else 'n/a'} | Chunk: {chunk_index}]\n{text}")

        if chunk_id not in sources_map:
            sources_map[chunk_id] = {
                "document_id": str(doc_id),
                "document_name": str(filename),
                "filename": str(filename),
                "page": int(page) if isinstance(page, (int, str)) and str(page).isdigit() else None,
                "chunk_index": int(chunk_index) if isinstance(chunk_index, (int, str)) and str(chunk_index).isdigit() else 0,
                "chunk_id": str(chunk_id),
                "relevance_score": rel_score,
                "text": text,
            }

    answer_text = generate_answer(query, context_blocks)

    answer_lower = answer_text.lower()
    is_grounded = not ("cannot be found" in answer_lower or "not found" in answer_lower or "not enough information" in answer_lower)

    return {
        "answer": answer_text,
        "sources": list(sources_map.values()),
        "grounded": is_grounded
    }