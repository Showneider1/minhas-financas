import pytest
from decimal import Decimal
from datetime import date, timedelta
from database.models import Goal, GoalStatus, GoalCategory
from services.goal_service import GoalService


class TestGoalService:

    def test_create_goal(self, db, sample_user):
        goal = GoalService.create_goal(
            db=db,
            user_id=sample_user.id,
            name="Viagem Europa",
            target_amount=Decimal("10000.00"),
            deadline=date.today() + timedelta(days=365),
            category=GoalCategory.TRAVEL,
        )
        assert goal.id is not None
        assert goal.name == "Viagem Europa"
        assert goal.target_amount == Decimal("10000.00")
        assert goal.current_amount == Decimal("0.00")
        assert goal.status == GoalStatus.ACTIVE

    def test_contribute_to_goal(self, db, sample_user):
        goal = GoalService.create_goal(
            db=db,
            user_id=sample_user.id,
            name="Reserva Emergencia",
            target_amount=Decimal("5000.00"),
            deadline=date.today() + timedelta(days=180),
        )
        updated = GoalService.contribute_to_goal(
            db=db, goal_id=goal.id, amount=Decimal("1000.00")
        )
        assert updated.current_amount == Decimal("1000.00")

    def test_goal_auto_completes_when_target_reached(self, db, sample_user):
        goal = GoalService.create_goal(
            db=db,
            user_id=sample_user.id,
            name="Notebook",
            target_amount=Decimal("3000.00"),
            deadline=date.today() + timedelta(days=90),
        )
        updated = GoalService.contribute_to_goal(
            db=db, goal_id=goal.id, amount=Decimal("3000.00")
        )
        assert updated.status == GoalStatus.COMPLETED

    def test_get_goals_by_user(self, db, sample_user):
        GoalService.create_goal(
            db=db,
            user_id=sample_user.id,
            name="Meta 1",
            target_amount=Decimal("1000.00"),
            deadline=date.today() + timedelta(days=30),
        )
        GoalService.create_goal(
            db=db,
            user_id=sample_user.id,
            name="Meta 2",
            target_amount=Decimal("2000.00"),
            deadline=date.today() + timedelta(days=60),
        )
        goals = GoalService.get_goals_by_user(db=db, user_id=sample_user.id)
        assert len(goals) == 2

    def test_get_goals_summary(self, db, sample_user):
        GoalService.create_goal(
            db=db,
            user_id=sample_user.id,
            name="Carro",
            target_amount=Decimal("20000.00"),
            deadline=date.today() + timedelta(days=720),
        )
        summary = GoalService.get_goals_summary(db=db, user_id=sample_user.id)
        assert "total_goals" in summary
        assert summary["total_goals"] >= 1

    def test_delete_goal(self, db, sample_user):
        goal = GoalService.create_goal(
            db=db,
            user_id=sample_user.id,
            name="Meta Temporaria",
            target_amount=Decimal("500.00"),
            deadline=date.today() + timedelta(days=10),
        )
        goal_id = goal.id
        GoalService.delete_goal(db=db, goal_id=goal_id)
        deleted = db.query(Goal).filter(Goal.id == goal_id).first()
        assert deleted is None

    def test_update_goal(self, db, sample_user):
        goal = GoalService.create_goal(
            db=db,
            user_id=sample_user.id,
            name="Meta Antiga",
            target_amount=Decimal("1500.00"),
            deadline=date.today() + timedelta(days=60),
        )
        updated = GoalService.update_goal(
            db=db,
            goal_id=goal.id,
            name="Meta Atualizada",
            target_amount=Decimal("2500.00"),
        )
        assert updated.name == "Meta Atualizada"
        assert updated.target_amount == Decimal("2500.00")

    def test_get_overdue_goals(self, db, sample_user):
        GoalService.create_goal(
            db=db,
            user_id=sample_user.id,
            name="Meta Vencida",
            target_amount=Decimal("1000.00"),
            deadline=date.today() - timedelta(days=1),
        )
        overdue = GoalService.get_overdue_goals(db=db, user_id=sample_user.id)
        assert len(overdue) >= 1
