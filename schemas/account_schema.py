from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal
from database.models.account import AccountType

class AccountBase(BaseModel):
    name: str
    account_type: AccountType
    initial_balance: Decimal = Decimal("0.00")
    color: Optional[str] = "#2ecc71"
    icon: Optional[str] = "bi-bank"
    
    # Novos campos opcionais
    credit_limit: Optional[Decimal] = Decimal("0.00")
    closing_day: Optional[int] = None
    due_day: Optional[int] = None

class AccountCreate(AccountBase):
    pass

class AccountUpdate(BaseModel):
    """Atualização parcial (todos opcionais)."""

    name: Optional[str] = None
    account_type: Optional[AccountType] = None
    initial_balance: Optional[Decimal] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    credit_limit: Optional[Decimal] = None
    closing_day: Optional[int] = None
    due_day: Optional[int] = None

class AccountResponse(AccountBase):
    id: int
    user_id: int
    balance: Decimal
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True