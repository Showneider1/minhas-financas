"""
Modelo de Transação Financeira.

Contrato canônico (P0 — ADR-002):
- `base_amount` (Numeric(12,2)) é o ÚNICO valor financeiro da transação.
  Não existe `amount/interest/discount/cashback` — ver CODE_AUDIT C1.
- Transferências: `transaction_type=TRANSFER` com `destination_account_id`
  preenchido; nunca entram em receitas/despesas (TransferService/BalanceService).
- "Pago" ≡ `status==PAID AND paid_date IS NOT NULL` (sincronizados em escrita).
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship

from database.base import Base
from database.enums import TransactionStatus, TransactionType  # canônicos (P1)

__all__ = ["Transaction", "TransactionType", "TransactionStatus"]


def _utcnow():
    """
    Retorna datetime atual em UTC timezone-aware.

    BUG 8 CORRIGIDO: substitui datetime.utcnow() depreciado no Python 3.12+.
    """
    return datetime.now(timezone.utc)


class Transaction(Base):
    """Modelo de Transação Financeira."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String(255), nullable=False)
    # Valor liquidado canônico. Numeric (nunca Float) — ADR-002.
    base_amount = Column(Numeric(12, 2), nullable=False)
    transaction_type = Column(Enum(TransactionType, native_enum=False), nullable=False)

    # Datas
    purchase_date = Column(Date, nullable=False, index=True)
    due_date = Column(Date, nullable=False, index=True)
    paid_date = Column(Date, nullable=True, index=True)

    # Status como coluna persistida (sincronizado com paid_date em escrita)
    status = Column(
        Enum(TransactionStatus, native_enum=False),
        default=TransactionStatus.PENDING,
        index=True,
    )

    # Parcelamento & Recorrência
    is_recurring = Column(Boolean, default=False)
    installment_number = Column(Integer, default=1)
    total_installments = Column(Integer, default=1)

    # Foreign Keys
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)

    # Transferência: conta destino (só para TRANSFER) + vínculo do par.
    destination_account_id = Column(
        Integer,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    # Grupo que vincula origem↔destino (mesmo valor nas duas pontas do par).
    transfer_group_id = Column(String(36), nullable=True, index=True)
    # Chave de idempotência de escrita (UUID v4 gerado no service).
    client_transfer_id = Column(String(36), nullable=True, unique=True, index=True)

    # Vínculo com a conta agendada que originou o lançamento (auditoria).
    scheduled_bill_id = Column(
        Integer,
        ForeignKey("scheduled_bills.id", ondelete="SET NULL"),
        nullable=True,
    )

    notes = Column(String(500), nullable=True)

    # Importacao bancaria em lote
    import_hash = Column(String(64), nullable=True, unique=True, index=True)
    categorization_source = Column(String(20), nullable=True, default="manual")

    # Cartão de crédito: transação vinculada ao cartão/fatura.
    credit_card_id = Column(
        Integer,
        ForeignKey("credit_cards.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    user = relationship("User", back_populates="transactions")
    account = relationship("Account", back_populates="transactions", foreign_keys=[account_id])
    destination_account = relationship("Account", foreign_keys=[destination_account_id])
    category = relationship("Category", back_populates="transactions")
    scheduled_bill = relationship("ScheduledBill", back_populates="transactions")
    credit_card = relationship("CreditCard", back_populates="transactions")

    __table_args__ = (
        Index("ix_transactions_user_paid", "user_id", "paid_date"),
        Index("ix_transactions_user_due", "user_id", "due_date"),
    )
