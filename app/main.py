import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.database import init_db
from app.database.seed import seed_dev_users
from app.api.rbac import router as rbac_router
from app.api.auth import router as auth_router
from app.api.documents import router as documents_router, admin_router as admin_documents_router
from app.api.retrieval import router as retrieval_router
from app.api.query import router as query_router, rag_router
from app.ingestion.loader import load_documents_from_directory
from app.ingestion.chunker import chunk_documents
from app.ingestion.embedder import embed_texts
from app.vectorstore.store import add_chunks, reset_collection
from app.retrieval.retriever import retrieve
from app.generation.generator import generate_answer

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and seed local dev users on startup
    init_db()
    seed_dev_users()
    yield


app = FastAPI(title="Secure RAG API", lifespan=lifespan)

# Configure CORS Middleware dynamically
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if "*" not in allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["Health Check"])
def health_check():
    """Health check endpoint for deployment monitoring."""
    return {"status": "healthy", "service": "Secure RAG API", "version": "2.4.0"}

app.include_router(auth_router)
app.include_router(rbac_router)
app.include_router(documents_router)
app.include_router(admin_documents_router)
app.include_router(retrieval_router)
app.include_router(query_router)
app.include_router(rag_router)


def ingest_pipeline(data_dir: Optional[Path] = None, reset: bool = True) -> int:
    """
    Load raw documents, split them into chunks, compute embeddings, and store in ChromaDB.
    """
    target_dir = data_dir or DATA_DIR
    print("--- Ingestion Phase ---")
    print(f"Loading documents from: {target_dir}")
    
    docs = load_documents_from_directory(target_dir)
    if not docs:
        print("No documents found to ingest.")
        return 0
    print(f"Loaded {len(docs)} document(s).")

    chunks = chunk_documents(docs, chunk_size=200, chunk_overlap=50)
    print(f"Created {len(chunks)} chunk(s) across all documents.")

    chunk_texts = [c["text"] for c in chunks]
    print(f"Generating embeddings for {len(chunk_texts)} chunk(s)...")
    embeddings = embed_texts(chunk_texts)

    if reset:
        print("Resetting vector collection before inserting new chunks...")
        reset_collection()

    print("Inserting chunks + embeddings + metadata into ChromaDB...")
    add_chunks(chunks, embeddings)
    print("Ingestion complete!\n")
    return len(chunks)


def run_naive_rag(query: str, top_k: int = 5, distance_threshold: float = 1.2) -> Dict[str, Any]:
    """
    Execute end-to-end Naive RAG query flow:
    Embed query -> Similarity Search -> Filter by distance threshold -> Context -> Gemini answer generation.
    """
    print(f"==================================================")
    print(f"QUERY: '{query}'")
    print(f"==================================================")
    
    retrieved_chunks = retrieve(query=query, top_k=top_k, distance_threshold=distance_threshold)
    
    print(f"\n--- Retrieved Chunks (top_k={top_k}, distance_threshold={distance_threshold}) ---")
    if not retrieved_chunks:
        print("No chunks passed the similarity-distance threshold!")
    else:
        for idx, chunk in enumerate(retrieved_chunks, 1):
            print(f"\n[{idx}] Chunk ID: {chunk['chunk_id']}")
            print(f"    Distance : {chunk['distance']:.4f}")
            print(f"    Metadata : {chunk['metadata']}")
            print(f"    Content  : {chunk['text']}")

    context_list = [c["text"] for c in retrieved_chunks]
    
    print("\n--- Generation (Gemini 3.6 Flash via Interactions API) ---")
    answer = generate_answer(query, context_list)
    print(f"Answer:\n{answer}\n")
    
    return {
        "query": query,
        "retrieved_chunks": retrieved_chunks,
        "answer": answer
    }


if __name__ == "__main__":
    init_db()
    seed_dev_users()
    ingest_pipeline()
    run_naive_rag("What is Python used for?", top_k=5, distance_threshold=1.2)
