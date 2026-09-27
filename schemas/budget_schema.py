from decimal import Decimal

from pydantic import BaseModel


class BudgetCreate(BaseModel):
    category_id: int
    amount: Decimal


class BudgetUpdate(BaseModel):
    amount: Decimal


class BudgetResponse(BaseModel):
    id: int
    category_name: str
    category_icon: str | None
    amount: Decimal
    spent: Decimal  # Quanto já gastou
    percentage: float  # % usado

    class Config:
        from_attributes = True
