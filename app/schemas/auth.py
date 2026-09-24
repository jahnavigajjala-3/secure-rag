from typing import Optional
from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    confirm_password: Optional[str] = None
    account_type: Optional[str] = "employee"
    admin_access_key: Optional[str] = None

class AdminRegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    invitation_code: str

class UserAuthResponse(BaseModel):
    id: str
    email: str
    role: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserAuthResponse

class RegisterResponse(BaseModel):
    message: str
    user: UserAuthResponse
