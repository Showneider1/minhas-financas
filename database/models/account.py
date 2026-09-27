"""
Model de conta bancária/financeira.
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, Enum as SQLEnum,
    Numeric,
)
from sqlalchemy.orm import relationship
from database.base import Base
from database.enums import AccountType  # canônico (P1) — re-export p/ compat
from database.mixins import TimestampMixin, SoftDeleteMixin

__all__ = ["Account", "AccountType"]


class Account(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "accounts"

    id   = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)

    account_type = Column(SQLEnum(AccountType, native_enum=False), default=AccountType.CHECKING, nullable=False)
    currency     = Column(String(3), default="BRL", nullable=False)

    # Saldos. Numeric (nunca Float) — ADR-002. `balance` é cache do
    # BalanceService (fonte: initial + transações); nunca editado à mão.
    balance         = Column(Numeric(12, 2), default=0, nullable=False)
    initial_balance = Column(Numeric(12, 2), default=0, nullable=False)

    credit_limit = Column(Numeric(12, 2), default=0, nullable=True)
    closing_day  = Column(Integer, nullable=True)
    due_day      = Column(Integer, nullable=True)

    color = Column(String(20), default="#2ecc71", nullable=False)
    icon  = Column(String(50), default="bi-bank",  nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    user_id         = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user            = relationship("User",          back_populates="accounts")
    # Duas FKs transactions->accounts existem (origem + destino); a coleção
    # usa a de origem. Destino acessado via Transaction.destination_account.
    transactions    = relationship("Transaction",   back_populates="account",
                                   foreign_keys="Transaction.account_id", lazy="dynamic")
    goals           = relationship("Goal",          back_populates="account")
    scheduled_bills = relationship("ScheduledBill", back_populates="account")

    def __repr__(self):
        return f"<Account(id={self.id}, name='{self.name}', type='{self.account_type}')>"