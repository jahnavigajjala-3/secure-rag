from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class RetrievalRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    distance_threshold: Optional[float] = 1.2

class ChunkMetadata(BaseModel):
    document_id: Optional[str] = None
    filename: Optional[str] = None
    source: Optional[str] = None
    filepath: Optional[str] = None
    page: Optional[int] = 1
    chunk_index: Optional[int] = 0

class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    distance: float
    metadata: Dict[str, Any]

class RetrievalResponse(BaseModel):
    query: str
    retrieved_chunks: List[RetrievedChunk]
    count: int
