"""
Model de conta bancária/financeira.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from database.base import Base
from database.mixins import TimestampMixin, SoftDeleteMixin
import enum


class AccountType(str, enum.Enum):
    CHECKING    = "checking"
    SAVINGS     = "savings"
    INVESTMENT  = "investment"
    CREDIT_CARD = "credit_card"
    CASH        = "cash"
    OTHER       = "other"


class Account(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "accounts"

    id   = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)

    account_type = Column(SQLEnum(AccountType), default=AccountType.CHECKING, nullable=False)
    currency     = Column(String(3), default="BRL", nullable=False)

    balance         = Column(Float, default=0.0, nullable=False)
    initial_balance = Column(Float, default=0.0, nullable=False)

    credit_limit = Column(Float,   default=0.0, nullable=True)
    closing_day  = Column(Integer, nullable=True)
    due_day      = Column(Integer, nullable=True)

    color = Column(String(20), default="#2ecc71", nullable=False)
    icon  = Column(String(50), default="bi-bank",  nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user            = relationship("User",          back_populates="accounts")
    transactions    = relationship("Transaction",   back_populates="account", lazy="dynamic")
    goals           = relationship("Goal",          back_populates="account")
    scheduled_bills = relationship("ScheduledBill", back_populates="account")

    def __repr__(self):
        return f"<Account(id={self.id}, name='{self.name}', type='{self.account_type}')>"