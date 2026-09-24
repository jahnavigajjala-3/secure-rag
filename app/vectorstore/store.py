import os
from typing import List, Dict, Any, Optional
import chromadb

CHROMA_PATH = os.getenv("CHROMA_PATH", "./data/chroma")
COLLECTION_NAME = "chunks"

_client: Optional[Any] = None


def get_chroma_client() -> Any:
    """
    Directly use PersistentClient.
    Bypasses HttpClient to prevent recursive port 8000 deadlocks.
    """
    global _client
    if _client is None:
        os.makedirs(CHROMA_PATH, exist_ok=True)
        _client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _client


def get_collection(
    client: Optional[Any] = None, 
    name: str = COLLECTION_NAME
) -> chromadb.Collection:
    """
    Get or create a ChromaDB collection with cosine distance metric.
    """
    if client is None:
        client = get_chroma_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"}
    )


def add_chunks(
    chunks: List[Dict[str, Any]], 
    embeddings: List[List[float]],
    collection_name: str = COLLECTION_NAME
) -> None:
    """
    Store chunk records and their embeddings in ChromaDB.
    """
    if not chunks:
        return

    collection = get_collection(name=collection_name)
    
    ids = [c["chunk_id"] for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    
    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )


def query_chunks(
    query_embedding: List[float], 
    top_k: int = 5,
    where: Optional[Dict[str, Any]] = None,
    collection_name: str = COLLECTION_NAME
) -> Dict[str, Any]:
    """
    Query ChromaDB for top-k similar chunks using query embedding and optional metadata filter.
    """
    collection = get_collection(name=collection_name)
    query_kwargs: Dict[str, Any] = {
        "query_embeddings": [query_embedding],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"]
    }
    if where:
        query_kwargs["where"] = where
        
    results = collection.query(**query_kwargs)
    return results


def delete_chunks_by_document_id(document_id: str, collection_name: str = COLLECTION_NAME) -> None:
    """
    Delete all vector chunks in ChromaDB belonging to a specific document_id.
    """
    try:
        collection = get_collection(name=collection_name)
        collection.delete(where={"document_id": str(document_id)})
    except Exception as e:
        print(f"Warning: Failed to delete Chroma chunks for document {document_id}: {e}")


def reset_collection(collection_name: str = COLLECTION_NAME) -> None:
    """
    Clear and re-create collection for testing or re-indexing.
    """
    client = get_chroma_client()
    try:
        client.delete_collection(name=collection_name)
    except Exception:
        pass
    client.get_or_create_collection(name=collection_name) 