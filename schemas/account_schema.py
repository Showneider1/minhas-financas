from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from database.models.account import AccountType


class AccountBase(BaseModel):
    name: str
    account_type: AccountType
    initial_balance: Decimal = Decimal("0.00")
    color: str | None = "#2ecc71"
    icon: str | None = "bi-bank"

    # Novos campos opcionais
    credit_limit: Decimal | None = Decimal("0.00")
    closing_day: int | None = None
    due_day: int | None = None


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    """Atualização parcial (todos opcionais)."""

    name: str | None = None
    account_type: AccountType | None = None
    initial_balance: Decimal | None = None
    color: str | None = None
    icon: str | None = None
    credit_limit: Decimal | None = None
    closing_day: int | None = None
    due_day: int | None = None


class AccountResponse(AccountBase):
    id: int
    user_id: int
    balance: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True
