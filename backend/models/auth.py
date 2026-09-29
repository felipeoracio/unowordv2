"""Supabase Auth request/response contracts."""

from pydantic import BaseModel, EmailStr, Field


class AuthCredentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class AuthUser(BaseModel):
    id: str
    email: str | None = None


class AuthResult(BaseModel):
    user: AuthUser
    authenticated: bool
    message: str