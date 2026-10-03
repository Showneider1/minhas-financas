"""
Modelo de Caixinhas (Virtual Vaults/Envelopes).
Caixinhas são divisões lógicas do patrimônio - NÃO são contas bancárias.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship

from database.base import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Vault(Base):
    """
    Caixinha para segregação lógica de saldo.
    saved_amount representa valor reservado na caixinha.
    target_amount representa meta a ser atingida.
    """

    __tablename__ = "vaults"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    target_amount = Column(Numeric(12, 2), nullable=False, default=0)
    saved_amount = Column(Numeric(12, 2), nullable=False, default=0)
    deadline = Column(Date, nullable=True)
    color = Column(String(7), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="vaults")

    __table_args__ = (
        CheckConstraint("saved_amount >= 0", name="ck_vault_saved_non_negative"),
    )
