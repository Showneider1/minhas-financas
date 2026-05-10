"""Model de Metas Financeiras."""
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from database.base import Base


def _utcnow():
    return datetime.now(timezone.utc)


class GoalStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class GoalCategory(str, enum.Enum):
    EMERGENCY_FUND = "emergency_fund"
    TRAVEL = "travel"
    EDUCATION = "education"
    PROPERTY = "property"
    VEHICLE = "vehicle"
    RETIREMENT = "retirement"
    INVESTMENT = "investment"
    OTHER = "other"


class Goal(Base):
    """Modelo de Meta Financeira.

    Permite que o usuario defina objetivos de poupanca com:
    - Valor alvo e prazo
    - Calculo automatico de quanto poupar por mes
    - Vinculo com conta bancaria especifica
    - Progresso percentual em tempo real
    """

    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)

    # Dados da meta
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(Enum(GoalCategory), default=GoalCategory.OTHER, nullable=False)

    # Valores
    target_amount = Column(Float, nullable=False)   # Valor alvo
    current_amount = Column(Float, default=0.0)     # Valor acumulado atual
    monthly_contribution = Column(Float, nullable=True)  # Contribuicao mensal sugerida

    # Prazo
    deadline = Column(DateTime(timezone=True), nullable=True)

    # Status
    status = Column(Enum(GoalStatus), default=GoalStatus.ACTIVE, nullable=False, index=True)
    is_deleted = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relacionamentos
    user = relationship("User", back_populates="goals")
    account = relationship("Account", back_populates="goals")

    @property
    def progress_percent(self) -> float:
        """Retorna o percentual de progresso da meta (0-100)."""
        if self.target_amount <= 0:
            return 0.0
        return min(round((self.current_amount / self.target_amount) * 100, 2), 100.0)

    @property
    def remaining_amount(self) -> float:
        """Retorna o valor restante para atingir a meta."""
        return max(self.target_amount - self.current_amount, 0.0)

    @property
    def months_to_deadline(self) -> int | None:
        """Calcula quantos meses restam ate o prazo."""
        if not self.deadline:
            return None
        now = datetime.now(timezone.utc)
        deadline = self.deadline
        if deadline.tzinfo is None:
            from datetime import timezone as tz
            deadline = deadline.replace(tzinfo=tz.utc)
        diff_days = (deadline - now).days
        return max(int(diff_days / 30), 0)

    @property
    def suggested_monthly_contribution(self) -> float | None:
        """Calcula a contribuicao mensal necessaria para atingir a meta no prazo."""
        months = self.months_to_deadline
        if not months or months <= 0:
            return None
        return round(self.remaining_amount / months, 2)

    def __repr__(self) -> str:
        return f"<Goal id={self.id} name='{self.name}' progress={self.progress_percent}%>"
