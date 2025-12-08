from pydantic import BaseModel, EmailStr
from uuid import UUID


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    role: str


class AdminCreateRequest(BaseModel):
    email: EmailStr
    password: str


class AdminCreateResponse(BaseModel):
    id: UUID
    email: str
    created_at: str

