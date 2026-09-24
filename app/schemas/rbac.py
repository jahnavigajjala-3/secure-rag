from typing import List
from pydantic import BaseModel, ConfigDict

class RoleCreate(BaseModel):
    name: str

class RoleResponse(BaseModel):
    id: str
    name: str

    model_config = ConfigDict(from_attributes=True)

class UserCreate(BaseModel):
    username: str

class UserResponse(BaseModel):
    id: str
    username: str
    roles: List[RoleResponse] = []

    model_config = ConfigDict(from_attributes=True)
