"""
Schemas para operações com categorias.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, validator

from database.models.category import TransactionType


class CategoryBase(BaseModel):
    """Base comum para Category schemas."""

    name: str = Field(..., min_length=2, max_length=100)
    type: TransactionType
    icon: str | None = Field(None, max_length=50)
    color: str | None = Field(None, max_length=7)

    @validator("color")
    def validate_color(cls, v):
        """Valida formato hexadecimal de cor."""
        if v and not v.startswith("#"):
            raise ValueError("Cor deve começar com #")
        if v and len(v) != 7:
            raise ValueError("Cor deve ter formato #RRGGBB")
        return v


class CategoryCreate(CategoryBase):
    """Schema para criação de categoria."""

    parent_id: int | None = None


class CategoryUpdate(BaseModel):
    """Schema para atualização de categoria."""

    name: str | None = Field(None, min_length=2, max_length=100)
    icon: str | None = Field(None, max_length=50)
    color: str | None = Field(None, max_length=7)
    is_active: bool | None = None


class CategoryResponse(CategoryBase):
    """Schema de resposta com dados da categoria."""

    id: int
    is_active: bool
    user_id: int | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @property
    def is_custom(self) -> bool:
        """Verifica se é categoria personalizada."""
        return self.user_id is not None


class CategoryWithStats(CategoryResponse):
    """Response estendido com estatísticas."""

    total_transactions: int = 0
    total_amount: Decimal = Decimal("0.00")
    percentage: float = 0.0  # Percentual em relação ao total
