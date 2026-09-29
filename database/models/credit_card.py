"""Modelo de Cartão de Crédito."""

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database.base import Base
from database.mixins import TimestampMixin


class CreditCard(Base, TimestampMixin):
    """Cartão de crédito com ciclo de fatura próprio."""

    __tablename__ = "credit_cards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id = Column(
        Integer,
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    credit_limit = Column(Numeric(12, 2), nullable=False)
    closing_day = Column(Integer, nullable=False)
    due_day = Column(Integer, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    transactions = relationship(
        "Transaction",
        back_populates="credit_card",
        foreign_keys="Transaction.credit_card_id",
        lazy="dynamic",
    )

    __table_args__ = (UniqueConstraint("account_id", name="uq_credit_cards_account"),)

    def __repr__(self) -> str:
        return (
            f"<CreditCard(id={self.id}, name='{self.name}', "
            f"limit={self.credit_limit}, closing_day={self.closing_day}, "
            f"due_day={self.due_day})>"
        )
