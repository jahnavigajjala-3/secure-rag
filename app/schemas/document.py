from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.rbac import RoleResponse

class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_size: int
    chunk_count: int
    status: str
    uploaded_at: str
    uploaded_by: Optional[str] = None
    accessible_roles: List[str] = []

    model_config = ConfigDict(from_attributes=True)


class DocumentAccessUpdateRequest(BaseModel):
    allowed_roles: List[str]

