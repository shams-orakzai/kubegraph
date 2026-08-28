"""Auth API schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

ROLES = {"engineer", "platform", "ciso"}


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    org: str = Field(default="", max_length=120)
    role: str = Field(default="engineer")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    org: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
