# schemas.py
from pydantic import BaseModel, field_validator
from typing import Optional
import re

# 1. Mahsulot sxemalari
class ItemCreate(BaseModel):
    name: str
    price: float
    description: Optional[str] = None

class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    description: Optional[str] = None
    owner_id: Optional[int] = None # Egasining ID sini ham qaytaramiz

    class Config:
        from_attributes = True

# 2. Foydalanuvchi sxemalari
class UserCreate(BaseModel):
    username: str
    password: str
    role: Optional[str] = "user"

    # Parol xavfsizligini tekshirish uchun Validator
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Parol kamida 8 ta belgidan iborat bo'lishi kerak!")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Parolda kamida bitta katta harf (A-Z) bo'lishi shart!")
        if not re.search(r"\d", v):
            raise ValueError("Parolda kamida bitta raqam (0-9) bo'lishi shart!")
        return v

class UserResponse(BaseModel):
    id: int
    username: str
    role: str

    class Config:
        from_attributes = True

# 3. Token sxemalari
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenRefreshRequest(BaseModel):
    refresh_token: str
