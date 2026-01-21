from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from database.models.account import AccountType

class AccountBase(BaseModel):
    name: str
    account_type: AccountType
    initial_balance: float = 0.0
    color: Optional[str] = "#2ecc71"
    icon: Optional[str] = "bi-bank"
    
    # Novos campos opcionais
    credit_limit: Optional[float] = 0.0
    closing_day: Optional[int] = None
    due_day: Optional[int] = None

class AccountCreate(AccountBase):
    pass

class AccountUpdate(AccountBase):
    name: Optional[str] = None
    account_type: Optional[AccountType] = None

class AccountResponse(AccountBase):
    id: int
    user_id: int
    balance: float
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True