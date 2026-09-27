"""
Schemas comuns reutilizáveis.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

# TypeVar para responses paginados genéricos
T = TypeVar("T")


class SuccessResponse(BaseModel):
    """Response padrão de sucesso."""

    success: bool = True
    message: str
    data: Any | None = None


class ErrorResponse(BaseModel):
    """Response padrão de erro."""

    success: bool = False
    error: str
    details: dict | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PaginatedResponse(BaseModel, Generic[T]):
    """Response paginado genérico."""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ):
        """Factory method para criar response paginado."""
        total_pages = (total + page_size - 1) // page_size
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )


class TokenResponse(BaseModel):
    """Response de autenticação com token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos
    user_id: int
    email: str
    name: str = ""
    # P1: refresh persistido no servidor (rotação/denylist); opcional p/ compat.
    refresh_token: str | None = None


class FilterBase(BaseModel):
    """Base para filtros com paginação."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)
    sort_by: str | None = None
    sort_desc: bool = False
