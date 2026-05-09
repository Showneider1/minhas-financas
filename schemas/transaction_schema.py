"""
Schemas Pydantic para Validação e Serialização de Transações.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import date, datetime
import enum

# ──────────────────────────────────────────────────────────────────
# BUG 3 CORRIGIDO: Enums declarados aqui no schema, eliminando o
# acoplamento direto com os models SQLAlchemy.
#
# Antes: `from database.models.transaction import TransactionType, TransactionStatus`
#   → violava a separação de camadas: se o ORM mudasse, o schema quebrava.
#
# Agora: os Enums são definidos de forma independente no schema.
#   Os models ORM devem importar estes Enums (ou manter os seus próprios
#   compatíveis), garantindo que mudanças no ORM não impactem a camada
#   de validação/serialização.
# ──────────────────────────────────────────────────────────────────

class TransactionType(str, enum.Enum):
    """Tipo de transação — definido no schema para independência do ORM."""
    INCOME   = "INCOME"
    EXPENSE  = "EXPENSE"
    TRANSFER = "TRANSFER"


class TransactionStatus(str, enum.Enum):
    """Status da transação — definido no schema para independência do ORM."""
    PENDING   = "PENDING"
    PAID      = "PAID"
    CANCELLED = "CANCELLED"


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
    base_amount: float = Field(
        ...,
        gt=0,
        description="Valor absoluto da transação. Deve ser positivo.",
    )
    transaction_type: TransactionType = Field(
        ...,
        description="Tipo: INCOME (Receita), EXPENSE (Despesa) ou TRANSFER (Transferência)",
    )

    # Chaves Estrangeiras
    category_id: int = Field(..., description="ID da categoria associada")
    account_id:  int = Field(..., description="ID da conta bancária associada")

    # Datas
    purchase_date: date = Field(..., description="Data da competência/compra (Quando o fato ocorreu)")
    due_date:      date = Field(..., description="Data de vencimento (Quando deve ser pago)")
    paid_date: Optional[date] = Field(
        None,
        description="Data da liquidação (Quando o dinheiro saiu). Se null, está Pendente.",
    )

    # Parcelamento & Recorrência
    is_recurring:       bool = Field(False, description="Indica se é uma assinatura recorrente (ex: Netflix)")
    installment_number: int  = Field(1, ge=1, description="Número da parcela atual (ex: 1)")
    total_installments: int  = Field(1, ge=1, description="Total de parcelas (ex: 12)")

    notes: Optional[str] = Field(None, max_length=500, description="Observações ou detalhes extras")

    # Validação de lógica de negócio
    @validator("installment_number")
    def validate_installment_logic(cls, v, values):
        """Garante que a parcela atual não seja maior que o total."""
        total = values.get("total_installments")
        if total and v > total:
            raise ValueError(f"Parcela atual ({v}) não pode ser maior que o total ({total})")
        return v


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
    description:        Optional[str]             = Field(None, min_length=3, max_length=255)
    base_amount:        Optional[float]            = Field(None, gt=0)
    transaction_type:   Optional[TransactionType] = None
    category_id:        Optional[int]             = None
    account_id:         Optional[int]             = None

    purchase_date: Optional[date] = None
    due_date:      Optional[date] = None
    paid_date:     Optional[date] = None

    is_recurring:       Optional[bool] = None
    installment_number: Optional[int]  = Field(None, ge=1)
    total_installments: Optional[int]  = Field(None, ge=1)
    notes:              Optional[str]  = None

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
    id:         int
    user_id:    int
    status:     TransactionStatus
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

    month:      Optional[int]  = Field(None, ge=1, le=12)
    year:       Optional[int]  = Field(None, ge=2000)
    start_date: Optional[date] = None
    end_date:   Optional[date] = None

    description:      Optional[str]             = None
    transaction_type: Optional[TransactionType] = None
    category_id:      Optional[int]             = None
    account_id:       Optional[int]             = None
    status:           Optional[TransactionStatus] = None

    sort_by:   Optional[str] = Field("date", description="Campo para ordenação")
    sort_desc: bool = True
    limit:     int  = 100
    offset:    int  = 0
