from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class RoleCreate(BaseModel):
    name: str


class RoleResponse(BaseModel):
    id: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    role_ids: Optional[List[str]] = None


class UserResponse(BaseModel):
    id: str
    username: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    roles: List[RoleResponse] = []

    model_config = ConfigDict(from_attributes=True)


class UserCreateResponse(UserResponse):
    plaintext_password: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
