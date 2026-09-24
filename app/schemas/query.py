from typing import List, Optional
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    distance_threshold: Optional[float] = 1.2

class SourceCitation(BaseModel):
    document_id: str
    filename: str
    page: Optional[int] = 1
    chunk_id: str
    relevance_score: float

class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[SourceCitation] = []
    grounded: bool
    retrieved_chunk_count: int
