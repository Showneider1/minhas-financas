from pydantic import BaseModel
from typing import Optional

class BudgetCreate(BaseModel):
    category_id: int
    amount: float

class BudgetUpdate(BaseModel):
    amount: float

class BudgetResponse(BaseModel):
    id: int
    category_name: str
    category_icon: Optional[str]
    amount: float
    spent: float  # Quanto já gastou
    percentage: float  # % usado

    class Config:
        from_attributes = True