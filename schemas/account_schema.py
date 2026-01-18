"""
Schemas de validação para contas.
"""
from pydantic import BaseModel, Field
from typing import Optional
from database.models.account import AccountType


class AccountCreate(BaseModel):
    """Schema para criação de conta."""
    name: str = Field(..., min_length=1, max_length=100)
    account_type: AccountType
    initial_balance: float = Field(default=0.0)
    color: str = Field(default="#2ecc71")  # ← ADICIONAR ESTA LINHA


class AccountUpdate(BaseModel):
    """Schema para atualização de conta."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    account_type: Optional[AccountType] = None
    color: Optional[str] = None  # ← ADICIONAR ESTA LINHA


class AccountResponse(BaseModel):
    """Schema de resposta de conta."""
    id: int
    name: str
    account_type: AccountType
    initial_balance: float
    current_balance: float
    color: str
    user_id: int
    
    class Config:
        from_attributes = True
