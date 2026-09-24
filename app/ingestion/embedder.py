from typing import List, Union
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
_model = None

def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def embed_text(text: str) -> List[float]:
    """
    Generate embedding for a single text string.
    Returns a 384-dimensional vector as a list of floats.
    """
    model = get_model()
    embedding = model.encode(text)
    if hasattr(embedding, "tolist"):
        return embedding.tolist()
    return list(embedding)

def embed_query(query: str) -> List[float]:
    """
    Generate embedding vector for a single query string.
    """
    return embed_text(query)

def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of text strings in batch.
    """
    if not texts:
        return []
    model = get_model()
    embeddings = model.encode(texts)
    if hasattr(embeddings, "tolist"):
        return embeddings.tolist()
    return [list(e) for e in embeddings]