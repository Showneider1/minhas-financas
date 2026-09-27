from pydantic import BaseModel
from typing import Optional
from decimal import Decimal

class BudgetCreate(BaseModel):
    category_id: int
    amount: Decimal

class BudgetUpdate(BaseModel):
    amount: Decimal

class BudgetResponse(BaseModel):
    id: int
    category_name: str
    category_icon: Optional[str]
    amount: Decimal
    spent: Decimal  # Quanto já gastou
    percentage: float  # % usado

    class Config:
        from_attributes = True