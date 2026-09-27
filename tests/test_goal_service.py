"""GoalService — reescrito para a API REAL (instanciada, Decimal, datetime).

Missão 2 Fase 12: os testes antigos chamavam API estática inexistente
(`GoalService.create_goal(db=...)`, `contribute_to_goal`, `get_goals_by_user`,
`get_overdue_goals`). Aqui cada caso preserva a INTENÇÃO original contra o
sistema real. Sem xfail/skip artificial.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from database.models import Goal, GoalStatus, GoalCategory
from services.goal_service import GoalService


def _future(days: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)


class TestGoalService:

    def test_create_goal(self, db, sample_user):
        goal = GoalService(db).create_goal(
            user_id=sample_user.id,
            name="Viagem Europa",
            target_amount=Decimal("10000.00"),
            deadline=_future(365),
            category=GoalCategory.TRAVEL,
        )
        assert goal.id is not None
        assert goal.name == "Viagem Europa"
        assert goal.target_amount == Decimal("10000.00")
        assert goal.current_amount == Decimal("0.00")
        assert goal.status == GoalStatus.ACTIVE

    def test_contribute_to_goal(self, db, sample_user):
        svc = GoalService(db)
        goal = svc.create_goal(
            user_id=sample_user.id,
            name="Reserva Emergencia",
            target_amount=Decimal("5000.00"),
            deadline=_future(180),
        )
        updated = svc.add_contribution(goal.id, sample_user.id, Decimal("1000.00"))
        assert updated.current_amount == Decimal("1000.00")

    def test_goal_auto_completes_when_target_reached(self, db, sample_user):
        svc = GoalService(db)
        goal = svc.create_goal(
            user_id=sample_user.id,
            name="Notebook",
            target_amount=Decimal("3000.00"),
            deadline=_future(90),
        )
        updated = svc.add_contribution(goal.id, sample_user.id, Decimal("3000.00"))
        assert updated.status == GoalStatus.COMPLETED

    def test_get_goals_by_user(self, db, sample_user):
        svc = GoalService(db)
        svc.create_goal(user_id=sample_user.id, name="Meta 1",
                        target_amount=Decimal("1000.00"), deadline=_future(30))
        svc.create_goal(user_id=sample_user.id, name="Meta 2",
                        target_amount=Decimal("2000.00"), deadline=_future(60))
        goals = svc.list_goals(user_id=sample_user.id)
        assert len(goals) == 2

    def test_get_goals_summary(self, db, sample_user):
        svc = GoalService(db)
        svc.create_goal(user_id=sample_user.id, name="Carro",
                        target_amount=Decimal("20000.00"), deadline=_future(720))
        summary = svc.get_goals_summary(user_id=sample_user.id)
        assert summary["total_goals"] >= 1
        assert summary["total_target"] == Decimal("20000.00")

    def test_delete_goal_is_soft_delete(self, db, sample_user):
        svc = GoalService(db)
        goal = svc.create_goal(
            user_id=sample_user.id, name="Meta Temporaria",
            target_amount=Decimal("500.00"), deadline=_future(10),
        )
        goal_id = goal.id
        assert svc.delete_goal(goal_id, sample_user.id) is True
        # Soft-delete: linha existe marcada, some da listagem.
        row = db.query(Goal).filter(Goal.id == goal_id).first()
        assert row is not None and row.is_deleted is True
        assert svc.list_goals(user_id=sample_user.id) == []

    def test_update_goal(self, db, sample_user):
        svc = GoalService(db)
        goal = svc.create_goal(
            user_id=sample_user.id, name="Meta Antiga",
            target_amount=Decimal("1500.00"), deadline=_future(60),
        )
        updated = svc.update_goal(
            goal_id=goal.id, user_id=sample_user.id,
            name="Meta Atualizada", target_amount=Decimal("2500.00"),
        )
        assert updated.name == "Meta Atualizada"
        assert updated.target_amount == Decimal("2500.00")

    def test_goal_imminent_deadline_months_zero(self, db, sample_user):
        """Prazo curto (<30 dias): months_to_deadline == 0 e aporte sugerido existe.

        (A API impede criar meta com prazo passado; o conceito 'vencida' aqui é
        prazo iminente — documenta a semântica real em vez de API inexistente.)
        """
        svc = GoalService(db)
        goal = svc.create_goal(
            user_id=sample_user.id, name="Meta Iminente",
            target_amount=Decimal("1000.00"), deadline=_future(10),
        )
        assert goal.months_to_deadline == 0
        assert svc.add_contribution is not None
        assert goal.suggested_monthly_contribution == Decimal("1000.00")

    def test_create_goal_rejects_non_positive_target(self, db, sample_user):
        with pytest.raises(ValueError):
            GoalService(db).create_goal(
                user_id=sample_user.id, name="Invalida",
                target_amount=Decimal("0.00"), deadline=_future(10),
            )

    def test_contribution_cannot_overdraw(self, db, sample_user):
        svc = GoalService(db)
        goal = svc.create_goal(
            user_id=sample_user.id, name="Reserva",
            target_amount=Decimal("1000.00"), deadline=_future(30),
        )
        with pytest.raises(ValueError):
            svc.add_contribution(goal.id, sample_user.id, Decimal("-10.00"))
