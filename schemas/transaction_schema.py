"""
Schemas para operações com transações.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import date, datetime
from database.models.category import TransactionType
from database.models.transaction import TransactionStatus
from schemas.common import FilterBase


class TransactionBase(BaseModel):
    """Base comum para Transaction schemas."""
    description: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    base_amount: float = Field(..., gt=0)
    interest: float = Field(default=0.0, ge=0)
    discount: float = Field(default=0.0, ge=0)
    cashback: float = Field(default=0.0, ge=0)
    transaction_type: TransactionType
    due_date: date
    category_id: int
    account_id: int


class TransactionCreate(TransactionBase):
    """Schema para criação de transação."""
    is_recurring: bool = False
    paid_date: Optional[date] = None
    
    @validator('paid_date')
    def validate_paid_date(cls, v, values):
        """Se paid_date está preenchido, marca como pago automaticamente."""
        return v


class TransactionUpdate(BaseModel):
    """Schema para atualização de transação."""
    description: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    base_amount: Optional[float] = Field(None, gt=0)
    interest: Optional[float] = Field(None, ge=0)
    discount: Optional[float] = Field(None, ge=0)
    cashback: Optional[float] = Field(None, ge=0)
    due_date: Optional[date] = None
    paid_date: Optional[date] = None
    status: Optional[TransactionStatus] = None
    category_id: Optional[int] = None
    account_id: Optional[int] = None


class TransactionResponse(TransactionBase):
    """Schema de resposta com dados da transação."""
    id: int
    amount: float  # Valor final calculado
    status: TransactionStatus
    paid_date: Optional[date]
    is_recurring: bool
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    # Campos calculados
    is_paid: bool
    is_overdue: bool
    
    class Config:
        from_attributes = True


class TransactionWithRelations(TransactionResponse):
    """Response com dados relacionados."""
    category_name: str
    category_icon: Optional[str]
    category_color: Optional[str]
    account_name: str


class TransactionFilter(FilterBase):
    """Filtros para listagem de transações."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    transaction_type: Optional[TransactionType] = None
    status: Optional[TransactionStatus] = None
    category_ids: Optional[list[int]] = None
    account_ids: Optional[list[int]] = None
    min_amount: Optional[float] = Field(None, ge=0)
    max_amount: Optional[float] = Field(None, ge=0)
    search: Optional[str] = None  # Busca em description e notes
    is_recurring: Optional[bool] = None
    
    @validator('max_amount')
    def validate_amount_range(cls, v, values):
        """Valida que max_amount >= min_amount."""
        if v and 'min_amount' in values and values['min_amount']:
            if v < values['min_amount']:
                raise ValueError('max_amount deve ser maior que min_amount')
        return v
