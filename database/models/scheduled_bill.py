"""Model de Contas a Pagar e a Receber (ScheduledBill)."""
import enum
from datetime import datetime, timezone, date
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, Enum, Text, SmallInteger
from sqlalchemy.orm import relationship
from database.base import Base


def _utcnow():
    return datetime.now(timezone.utc)


class BillType(str, enum.Enum):
    PAYABLE = "payable"      # Conta a pagar
    RECEIVABLE = "receivable"  # Conta a receber


class BillStatus(str, enum.Enum):
    PENDING = "pending"        # Aguardando
    PAID = "paid"              # Pago/Recebido
    OVERDUE = "overdue"        # Vencido
    CANCELLED = "cancelled"    # Cancelado


class BillRecurrence(str, enum.Enum):
    NONE = "none"              # Nao se repete
    MONTHLY = "monthly"        # Mensal
    WEEKLY = "weekly"          # Semanal
    YEARLY = "yearly"          # Anual
    QUARTERLY = "quarterly"    # Trimestral


class ScheduledBill(Base):
    """Modelo de Conta a Pagar / Receber.

    Funcionalidades:
    - Controle de vencimentos futuros
    - Alertas X dias antes do vencimento
    - Recorrencia automatica
    - Vinculo com categoria e conta bancaria
    """

    __tablename__ = "scheduled_bills"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)

    # Dados da conta
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    bill_type = Column(Enum(BillType), nullable=False, index=True)

    # Valores
    amount = Column(Float, nullable=False)
    paid_amount = Column(Float, nullable=True)    # Valor efetivamente pago (pode divergir)

    # Datas
    due_date = Column(Date, nullable=False, index=True)     # Data de vencimento
    paid_date = Column(Date, nullable=True)                  # Data de pagamento

    # Status
    status = Column(Enum(BillStatus), default=BillStatus.PENDING, nullable=False, index=True)
    is_deleted = Column(Boolean, default=False)

    # Alertas
    reminder_days_before = Column(SmallInteger, default=3)   # Alertar X dias antes
    reminded_at = Column(DateTime(timezone=True), nullable=True)  # Ultima vez que alertou

    # Recorrencia
    recurrence = Column(Enum(BillRecurrence), default=BillRecurrence.NONE, nullable=False)
    parent_bill_id = Column(Integer, ForeignKey("scheduled_bills.id", ondelete="SET NULL"), nullable=True)

    # Observacoes
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relacionamentos
    user = relationship("User", back_populates="scheduled_bills")
    account = relationship("Account", back_populates="scheduled_bills")
    category = relationship("Category", back_populates="scheduled_bills")
    child_bills = relationship("ScheduledBill", foreign_keys=[parent_bill_id], backref="parent_bill")

    @property
    def is_overdue(self) -> bool:
        """Verifica se a conta esta vencida e nao paga."""
        if self.status in (BillStatus.PAID, BillStatus.CANCELLED):
            return False
        return date.today() > self.due_date

    @property
    def days_until_due(self) -> int:
        """Retorna quantos dias faltam para o vencimento (negativo se ja venceu)."""
        return (self.due_date - date.today()).days

    @property
    def should_remind(self) -> bool:
        """Verifica se deve enviar alerta (dentro do prazo de lembrete)."""
        if self.status in (BillStatus.PAID, BillStatus.CANCELLED):
            return False
        return 0 <= self.days_until_due <= self.reminder_days_before

    def __repr__(self) -> str:
        return f"<ScheduledBill id={self.id} name='{self.name}' due={self.due_date} status={self.status}>"
