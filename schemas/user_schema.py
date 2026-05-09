"""
Schemas para operações com usuários.
"""
from pydantic import BaseModel, Field, field_validator, validator
from typing import Optional
from datetime import datetime
import re


def validate_email_format(email: str) -> str:
    """Valida email com regex simples — aceita qualquer domínio válido."""
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValueError('Email inválido')
    return email.lower().strip()


class UserBase(BaseModel):
    """Base comum para User schemas."""
    email: str
    name: str = Field(..., min_length=2, max_length=200)

    @field_validator('email')
    @classmethod
    def validar_email(cls, v):
        return validate_email_format(v)


class UserCreate(UserBase):
    """Schema para criação de usuário."""
    password: str = Field(..., min_length=8, max_length=100)

    @validator('password')
    def validate_password(cls, v):
        """Valida complexidade da senha."""
        if not any(char.isdigit() for char in v):
            raise ValueError('Senha deve conter pelo menos um número')
        if not any(char.isupper() for char in v):
            raise ValueError('Senha deve conter pelo menos uma letra maiúscula')
        if not any(char.islower() for char in v):
            raise ValueError('Senha deve conter pelo menos uma letra minúscula')
        return v


class UserLogin(BaseModel):
    """Schema para login."""
    email: str
    password: str

    @field_validator('email')
    @classmethod
    def validar_email(cls, v):
        return validate_email_format(v)


class UserUpdate(BaseModel):
    """Schema para atualização de usuário."""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    email: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator('email', mode='before')
    @classmethod
    def validar_email(cls, v):
        if v is None:
            return v
        return validate_email_format(v)


class UserResponse(UserBase):
    """Schema de resposta com dados do usuário."""
    id: int
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserProfileResponse(UserResponse):
    """Response estendido com estatísticas."""
    total_accounts: int = 0
    total_transactions: int = 0
    total_balance: float = 0.0