"""Model de Contas a Pagar e a Receber (ScheduledBill)."""

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from database.base import Base
from database.enums import BillRecurrence, BillStatus, BillType  # canônicos (P1)

__all__ = ["ScheduledBill", "BillType", "BillStatus", "BillRecurrence"]


def _utcnow():
    return datetime.now(timezone.utc)


class ScheduledBill(Base):
    """Modelo de Conta a Pagar / Receber."""

    __tablename__ = "scheduled_bills"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)

    # Dados da conta
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    bill_type = Column(Enum(BillType, native_enum=False), nullable=False, index=True)

    # Valores (Numeric — nunca Float; ADR-002)
    amount = Column(Numeric(12, 2), nullable=False)
    paid_amount = Column(Numeric(12, 2), nullable=True)

    # Datas
    due_date = Column(Date, nullable=False, index=True)
    paid_date = Column(Date, nullable=True)

    # Status
    status = Column(
        Enum(BillStatus, native_enum=False), default=BillStatus.PENDING, nullable=False, index=True
    )
    is_deleted = Column(Boolean, default=False)
    # P1: pausa sem cancelar — bill pausado não gera recorrência nem alerta.
    is_paused = Column(Boolean, default=False, nullable=False, server_default="0")

    # Alertas
    reminder_days_before = Column(SmallInteger, default=3)
    reminded_at = Column(DateTime(timezone=True), nullable=True)

    # Recorrencia
    recurrence = Column(
        Enum(BillRecurrence, native_enum=False), default=BillRecurrence.NONE, nullable=False
    )
    parent_bill_id = Column(
        Integer, ForeignKey("scheduled_bills.id", ondelete="SET NULL"), nullable=True
    )

    # Observacoes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # ─── Relacionamentos ──────────────────────────────────────────────────────
    user = relationship("User", back_populates="scheduled_bills")
    account = relationship("Account", back_populates="scheduled_bills")
    category = relationship("Category", back_populates="scheduled_bills")

    # Auto-relacionamento: um pai tem vários filhos (recorrência)
    # child_bills  → lado ONETOMANY  (sem remote_side)
    # parent_bill  → lado MANYTOONE  (com remote_side=[id])
    child_bills = relationship(
        "ScheduledBill",
        foreign_keys=[parent_bill_id],
        back_populates="parent_bill",
    )

    parent_bill = relationship(
        "ScheduledBill",
        foreign_keys=[parent_bill_id],
        back_populates="child_bills",
        remote_side=[id],  # resolve o erro de direção
    )

    # Lançamentos gerados ao pagar a conta (rastreabilidade — Fase 6).
    transactions = relationship("Transaction", back_populates="scheduled_bill")

    __table_args__ = (
        Index("ix_bills_user_due_status", "user_id", "due_date", "status"),
        CheckConstraint("amount > 0", name="ck_bill_amount_positive"),
    )

    # ─── Properties ───────────────────────────────────────────────────────────
    @property
    def is_overdue(self) -> bool:
        if self.status in (BillStatus.PAID, BillStatus.CANCELLED):
            return False
        return date.today() > self.due_date

    @property
    def days_until_due(self) -> int:
        return (self.due_date - date.today()).days

    @property
    def should_remind(self) -> bool:
        if self.status in (BillStatus.PAID, BillStatus.CANCELLED):
            return False
        return 0 <= self.days_until_due <= self.reminder_days_before

    def __repr__(self) -> str:
        return (
            f"<ScheduledBill id={self.id} name='{self.name}' "
            f"due={self.due_date} status={self.status}>"
        )
