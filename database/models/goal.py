"""Model de Metas Financeiras."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

from database.base import Base
from database.enums import GoalCategory, GoalStatus  # canônicos (P1)

__all__ = ["Goal", "GoalStatus", "GoalCategory"]


def _utcnow():
    return datetime.now(timezone.utc)


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
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)

    # Dados da meta
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(
        Enum(GoalCategory, native_enum=False), default=GoalCategory.OTHER, nullable=False
    )

    # Valores (Numeric — nunca Float; ADR-002)
    target_amount = Column(Numeric(12, 2), nullable=False)  # Valor alvo
    current_amount = Column(Numeric(12, 2), default=0)  # Valor acumulado atual
    monthly_contribution = Column(Numeric(12, 2), nullable=True)  # Contribuicao mensal sugerida

    # Prazo
    deadline = Column(DateTime(timezone=True), nullable=True)

    # Status
    status = Column(
        Enum(GoalStatus, native_enum=False), default=GoalStatus.ACTIVE, nullable=False, index=True
    )
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
        target = Decimal(str(self.target_amount or 0))
        if target <= 0:
            return 0.0
        current = Decimal(str(self.current_amount or 0))
        return min(float((current / target) * 100), 100.0)

    @property
    def remaining_amount(self) -> Decimal:
        """Retorna o valor restante para atingir a meta (Decimal, nunca negativo)."""
        target = Decimal(str(self.target_amount or 0))
        current = Decimal(str(self.current_amount or 0))
        return max(target - current, Decimal("0.00"))

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
    def suggested_monthly_contribution(self) -> Decimal | None:
        """Contribuicao mensal necessaria (Decimal). None se prazo <= 0 dias.

        P0: <1 mês não retorna mais None indevidamente — usa teto de 1 mês
        quando há dias restantes (antes: 29 dias -> 0 meses -> None).
        """
        if not self.deadline:
            return None
        now = datetime.now(timezone.utc)
        deadline = self.deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        diff_days = (deadline - now).days
        if diff_days < 0:
            return None
        months = max(int(diff_days / 30), 1)
        return (self.remaining_amount / months).quantize(Decimal("0.01"))

    def __repr__(self) -> str:
        return f"<Goal id={self.id} name='{self.name}' progress={self.progress_percent}%>"
