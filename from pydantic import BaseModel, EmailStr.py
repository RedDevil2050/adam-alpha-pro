from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str
    exp: int
    scopes: list[str] = []

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    rate_limit: int = Field(default=100, gt=0)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class User(UserBase):
    id: str
    is_active: bool = True
    disabled: bool = False
