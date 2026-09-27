"""
Schemas Pydantic para Validação e Serialização de Transações.

Contrato canônico (P0 — ADR-002 + P1 unificação):
- `base_amount: Decimal` é o ÚNICO valor financeiro. Sem amount/interest/discount.
- Enums importados de `database.enums` (fonte única — P1 unifica os duplicados
  que existiam aqui; igualdade por identidade em toda a codebase).
- Transferências: `transaction_type=TRANSFER` exige `destination_account_id`.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator, validator

from database.enums import TransactionStatus, TransactionType

__all__ = [
    "TransactionType",
    "TransactionStatus",
    "TransactionBase",
    "TransactionCreate",
    "TransactionUpdate",
    "TransactionResponse",
    "TransactionFilter",
]


# ==========================================
# 1. BASE: Campos Comuns
# ==========================================
class TransactionBase(BaseModel):
    """
    Campos base compartilhados entre Criação e Leitura.
    """

    description: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Descrição curta da transação (ex: Mercado, Salário)",
    )
    base_amount: Decimal = Field(
        ...,
        gt=0,
        description="Valor liquidado canônico (Decimal, positivo).",
    )
    transaction_type: TransactionType = Field(
        ...,
        description="Tipo: INCOME (Receita), EXPENSE (Despesa) ou TRANSFER (Transferência)",
    )

    # Transferência: conta destino (obrigatória quando type=TRANSFER).
    destination_account_id: int | None = Field(
        None,
        description="Conta destino (apenas TRANSFER)",
    )

    # Chaves Estrangeiras
    category_id: int = Field(..., description="ID da categoria associada")
    account_id: int = Field(..., description="ID da conta bancária associada")

    # Datas
    purchase_date: date = Field(
        ..., description="Data da competência/compra (Quando o fato ocorreu)"
    )
    due_date: date = Field(..., description="Data de vencimento (Quando deve ser pago)")
    paid_date: date | None = Field(
        None,
        description="Data da liquidação (Quando o dinheiro saiu). Se null, está Pendente.",
    )

    # Parcelamento & Recorrência
    is_recurring: bool = Field(
        False, description="Indica se é uma assinatura recorrente (ex: Netflix)"
    )
    installment_number: int = Field(1, ge=1, description="Número da parcela atual (ex: 1)")
    total_installments: int = Field(1, ge=1, description="Total de parcelas (ex: 12)")

    notes: str | None = Field(None, max_length=500, description="Observações ou detalhes extras")

    # Validação de lógica de negócio
    @validator("installment_number")
    def validate_installment_logic(cls, v, values):
        """Garante que a parcela atual não seja maior que o total."""
        total = values.get("total_installments")
        if total and v > total:
            raise ValueError(f"Parcela atual ({v}) não pode ser maior que o total ({total})")
        return v

    @model_validator(mode="after")
    def validate_transfer_destination(self):
        """TRANSFER exige destino diferente da origem (origem validada no service)."""
        if self.transaction_type == TransactionType.TRANSFER and not self.destination_account_id:
            raise ValueError("TRANSFER exige destination_account_id")
        if self.transaction_type != TransactionType.TRANSFER and self.destination_account_id:
            raise ValueError("destination_account_id só é permitido para TRANSFER")
        return self


# ==========================================
# 2. CREATE: Para criar novas
# ==========================================
class TransactionCreate(TransactionBase):
    """Schema usado no POST /transactions."""

    pass


# ==========================================
# 3. UPDATE: Para editar (Tudo Opcional)
# ==========================================
class TransactionUpdate(BaseModel):
    """
    Schema usado no PUT/PATCH. Todos os campos são opcionais para suportar
    atualizações parciais sem re-enviar todos os campos.
    """

    description: str | None = Field(None, min_length=3, max_length=255)
    base_amount: Decimal | None = Field(None, gt=0)
    transaction_type: TransactionType | None = None
    category_id: int | None = None
    account_id: int | None = None
    destination_account_id: int | None = None

    purchase_date: date | None = None
    due_date: date | None = None
    paid_date: date | None = None

    is_recurring: bool | None = None
    installment_number: int | None = Field(None, ge=1)
    total_installments: int | None = Field(None, ge=1)
    notes: str | None = None

    @validator("installment_number")
    def validate_installment_update(cls, v, values):
        total = values.get("total_installments")
        if total and v and v > total:
            raise ValueError("Parcela atual não pode ser maior que o total")
        return v


# ==========================================
# 4. RESPONSE: O que o Backend devolve
# ==========================================
class TransactionResponse(TransactionBase):
    """Schema completo retornado para o Frontend."""

    id: int
    user_id: int
    status: TransactionStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Permite converter objeto SQLAlchemy → Pydantic


# ==========================================
# 5. FILTER: Para o Dashboard e Extrato
# ==========================================
class TransactionFilter(BaseModel):
    """Schema avançado para filtrar dados no Service."""

    user_id: int

    month: int | None = Field(None, ge=1, le=12)
    year: int | None = Field(None, ge=2000)
    start_date: date | None = None
    end_date: date | None = None

    description: str | None = None
    transaction_type: TransactionType | None = None
    category_id: int | None = None
    account_id: int | None = None
    status: TransactionStatus | None = None

    sort_by: str | None = Field("date", description="Campo para ordenação")
    sort_desc: bool = True
    limit: int = 100
    offset: int = 0
