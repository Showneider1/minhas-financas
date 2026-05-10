"""
Modelo de Transação Financeira.
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database.base import Base
from database.models.category import TransactionType
import enum


def _utcnow():
    """
    Retorna datetime atual em UTC timezone-aware.

    BUG 8 CORRIGIDO: substitui datetime.utcnow() depreciado no Python 3.12+.
    """
    return datetime.now(timezone.utc)


class TransactionStatus(enum.Enum):
    """Status da transação."""
    PENDING   = "PENDING"
    PAID      = "PAID"
    CANCELLED = "CANCELLED"


class Transaction(Base):
    """Modelo de Transação Financeira."""
    __tablename__ = "transactions"

    id               = Column(Integer,      primary_key=True, index=True)
    description      = Column(String(255),  nullable=False)
    base_amount      = Column(Float,        nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)

    # Datas
    purchase_date = Column(Date, nullable=False, index=True)
    due_date      = Column(Date, nullable=False, index=True)
    paid_date     = Column(Date, nullable=True,  index=True)

    # Status como coluna persistida
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING, index=True)

    # Parcelamento & Recorrência
    is_recurring       = Column(Boolean, default=False)
    installment_number = Column(Integer, default=1)
    total_installments = Column(Integer, default=1)

    # Foreign Keys
    user_id     = Column(Integer, ForeignKey("users.id"),      nullable=False, index=True)
    account_id  = Column(Integer, ForeignKey("accounts.id"),   nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    notes = Column(String(500), nullable=True)

    # Importacao bancaria em lote
    import_hash           = Column(String(64), nullable=True, unique=True, index=True)
    categorization_source = Column(String(20), nullable=True, default="manual")

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    user     = relationship("User",     back_populates="transactions")
    account  = relationship("Account",  back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
