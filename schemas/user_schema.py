"""
Schemas para operações com usuários.
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base comum para User schemas."""
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=200)


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
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """Schema para atualização de usuário."""
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema de resposta com dados do usuário."""
    id: int
    is_active: bool
    is_verified: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True  # Pydantic v2 (antes era orm_mode)


class UserProfileResponse(UserResponse):
    """Response estendido com estatísticas."""
    total_accounts: int = 0
    total_transactions: int = 0
    total_balance: float = 0.0
