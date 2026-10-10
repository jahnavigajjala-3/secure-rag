from typing import List, Optional
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    distance_threshold: Optional[float] = 1.2

class SourceCitation(BaseModel):
    document_id: str
    document_name: Optional[str] = None
    filename: Optional[str] = None
    page: Optional[int] = None
    chunk_index: Optional[int] = None
    chunk_id: str
    relevance_score: float

class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[SourceCitation] = []
    grounded: bool
    retrieved_chunk_count: int
