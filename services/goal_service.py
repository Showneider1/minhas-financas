"""Servico de Metas Financeiras (Goal)."""
from datetime import datetime, timezone, date
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database.models.goal import Goal, GoalStatus, GoalCategory
from config.logging_config import app_logger


class GoalService:
    """CRUD e logica de negocio para Metas Financeiras.

    Responsabilidades:
    - Criar, editar, excluir (soft-delete) e listar metas
    - Calcular progresso percentual, valor restante e contribuicao mensal
    - Marcar metas como concluidas automaticamente ao atingir 100%
    - Fornecer dados para o dashboard de saude financeira
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ #
    # CRUD                                                                  #
    # ------------------------------------------------------------------ #

    def create_goal(
        self,
        user_id: int,
        name: str,
        target_amount: float,
        category: GoalCategory = GoalCategory.OTHER,
        description: Optional[str] = None,
        deadline: Optional[datetime] = None,
        account_id: Optional[int] = None,
        current_amount: float = 0.0,
    ) -> Goal:
        """Cria uma nova meta financeira.

        Args:
            user_id: ID do usuario dono da meta
            name: Nome da meta (ex: 'Viagem para Europa')
            target_amount: Valor alvo em R$
            category: Categoria da meta
            description: Descricao opcional
            deadline: Data limite para atingir a meta
            account_id: Conta bancaria vinculada (opcional)
            current_amount: Valor ja acumulado

        Returns:
            Goal criada e persistida

        Raises:
            ValueError: Se target_amount <= 0 ou current_amount < 0
        """
        if target_amount <= 0:
            raise ValueError("O valor alvo da meta deve ser maior que zero.")
        if current_amount < 0:
            raise ValueError("O valor atual nao pode ser negativo.")
        if deadline and deadline <= datetime.now(timezone.utc):
            raise ValueError("O prazo da meta deve ser uma data futura.")

        goal = Goal(
            user_id=user_id,
            name=name,
            target_amount=target_amount,
            current_amount=current_amount,
            category=category,
            description=description,
            deadline=deadline,
            account_id=account_id,
            status=GoalStatus.ACTIVE,
        )
        self.db.add(goal)
        self.db.commit()
        self.db.refresh(goal)
        app_logger.info(f"Meta criada: id={goal.id} user_id={user_id} nome='{name}'")
        return goal

    def get_goal(self, goal_id: int, user_id: int) -> Optional[Goal]:
        """Retorna uma meta pelo ID garantindo pertencer ao usuario."""
        return (
            self.db.query(Goal)
            .filter(
                and_(
                    Goal.id == goal_id,
                    Goal.user_id == user_id,
                    Goal.is_deleted.is_(False),
                )
            )
            .first()
        )

    def list_goals(
        self,
        user_id: int,
        status: Optional[GoalStatus] = None,
        category: Optional[GoalCategory] = None,
    ) -> List[Goal]:
        """Lista todas as metas do usuario com filtros opcionais."""
        query = self.db.query(Goal).filter(
            and_(Goal.user_id == user_id, Goal.is_deleted.is_(False))
        )
        if status:
            query = query.filter(Goal.status == status)
        if category:
            query = query.filter(Goal.category == category)
        return query.order_by(Goal.created_at.desc()).all()

    def update_goal(
        self,
        goal_id: int,
        user_id: int,
        **kwargs,
    ) -> Optional[Goal]:
        """Atualiza campos de uma meta existente.

        Campos suportados: name, description, target_amount,
        current_amount, deadline, account_id, category.
        """
        goal = self.get_goal(goal_id, user_id)
        if not goal:
            return None

        allowed_fields = {
            "name", "description", "target_amount",
            "current_amount", "deadline", "account_id", "category",
        }
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(goal, key, value)

        # Verifica se meta foi atingida apos atualizacao
        self._check_completion(goal)

        goal.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(goal)
        return goal

    def add_contribution(
        self,
        goal_id: int,
        user_id: int,
        amount: float,
    ) -> Optional[Goal]:
        """Adiciona uma contribuicao ao valor acumulado da meta.

        Args:
            goal_id: ID da meta
            user_id: ID do usuario
            amount: Valor a adicionar (positivo para deposito,
                    negativo para retirada)

        Returns:
            Meta atualizada ou None se nao encontrada
        """
        goal = self.get_goal(goal_id, user_id)
        if not goal:
            return None
        if goal.status == GoalStatus.CANCELLED:
            raise ValueError("Nao e possivel contribuir para uma meta cancelada.")

        new_amount = goal.current_amount + amount
        if new_amount < 0:
            raise ValueError("O valor acumulado nao pode ficar negativo.")

        goal.current_amount = new_amount
        self._check_completion(goal)
        goal.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(goal)
        app_logger.info(
            f"Contribuicao registrada: goal_id={goal_id} valor={amount:+.2f} "
            f"total={goal.current_amount:.2f} progresso={goal.progress_percent}%"
        )
        return goal

    def delete_goal(self, goal_id: int, user_id: int) -> bool:
        """Soft-delete de uma meta."""
        goal = self.get_goal(goal_id, user_id)
        if not goal:
            return False
        goal.is_deleted = True
        goal.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        return True

    def cancel_goal(self, goal_id: int, user_id: int) -> Optional[Goal]:
        """Cancela uma meta ativa ou pausada."""
        goal = self.get_goal(goal_id, user_id)
        if not goal:
            return None
        goal.status = GoalStatus.CANCELLED
        goal.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(goal)
        return goal

    # ------------------------------------------------------------------ #
    # ANALYTICS                                                             #
    # ------------------------------------------------------------------ #

    def get_goals_summary(self, user_id: int) -> Dict[str, Any]:
        """Retorna um resumo de todas as metas do usuario para o dashboard.

        Returns:
            Dict com:
            - total_goals: quantidade total de metas ativas
            - total_target: soma de todos os valores alvo
            - total_current: soma de todos os valores acumulados
            - overall_progress: progresso geral (%)
            - near_deadline: metas com prazo em <= 30 dias
            - completed_this_year: metas concluidas no ano corrente
        """
        active_goals = self.list_goals(user_id, status=GoalStatus.ACTIVE)

        total_target = sum(g.target_amount for g in active_goals)
        total_current = sum(g.current_amount for g in active_goals)
        overall_progress = (
            round((total_current / total_target) * 100, 2)
            if total_target > 0 else 0.0
        )

        now = datetime.now(timezone.utc)
        near_deadline = [
            {
                "id": g.id,
                "name": g.name,
                "days_left": g.months_to_deadline * 30 if g.months_to_deadline is not None else None,
                "progress": g.progress_percent,
                "remaining": g.remaining_amount,
                "monthly_needed": g.suggested_monthly_contribution,
            }
            for g in active_goals
            if g.deadline and g.months_to_deadline is not None and g.months_to_deadline <= 1
        ]

        current_year = now.year
        completed_this_year = (
            self.db.query(Goal)
            .filter(
                and_(
                    Goal.user_id == user_id,
                    Goal.status == GoalStatus.COMPLETED,
                    Goal.completed_at >= datetime(current_year, 1, 1, tzinfo=timezone.utc),
                )
            )
            .count()
        )

        return {
            "total_goals": len(active_goals),
            "total_target": round(total_target, 2),
            "total_current": round(total_current, 2),
            "overall_progress": overall_progress,
            "near_deadline": near_deadline,
            "completed_this_year": completed_this_year,
            "goals_detail": [
                {
                    "id": g.id,
                    "name": g.name,
                    "category": g.category.value,
                    "target": g.target_amount,
                    "current": g.current_amount,
                    "progress": g.progress_percent,
                    "remaining": g.remaining_amount,
                    "monthly_needed": g.suggested_monthly_contribution,
                    "deadline": g.deadline.isoformat() if g.deadline else None,
                }
                for g in active_goals
            ],
        }

    # ------------------------------------------------------------------ #
    # INTERNAL HELPERS                                                      #
    # ------------------------------------------------------------------ #

    def _check_completion(self, goal: Goal) -> None:
        """Marca a meta como concluida se o valor atual atingiu o alvo."""
        if (
            goal.status == GoalStatus.ACTIVE
            and goal.current_amount >= goal.target_amount
        ):
            goal.status = GoalStatus.COMPLETED
            goal.completed_at = datetime.now(timezone.utc)
            app_logger.info(
                f"Meta concluida automaticamente: id={goal.id} nome='{goal.name}'"
            )
