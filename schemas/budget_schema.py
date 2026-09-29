from decimal import Decimal

from pydantic import BaseModel


class BudgetCreate(BaseModel):
    category_id: int
    amount_limit: Decimal


class BudgetUpdate(BaseModel):
    amount_limit: Decimal


class BudgetResponse(BaseModel):
    id: int
    category_name: str
    category_icon: str | None
    amount_limit: Decimal
    spent: Decimal  # Quanto já gastou
    percentage: float  # % usado

    class Config:
        from_attributes = True
