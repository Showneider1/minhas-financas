"""Testes do BudgetService — limites, consumo e isolamento."""

from datetime import date
from decimal import Decimal

import pytest

from database.enums import TransactionStatus, TransactionType
from database.models.budget import Budget
from database.models.category import Category
from database.models.transaction import Transaction
from database.models.user import User
from services.budget_service import BudgetService


def _create_expense(db, user_id, account_id, category_id, amount, due_date):
    transaction = Transaction(
        user_id=user_id,
        account_id=account_id,
        category_id=category_id,
        description="Despesa de teste",
        base_amount=Decimal(amount),
        transaction_type=TransactionType.EXPENSE,
        purchase_date=due_date,
        due_date=due_date,
        paid_date=due_date,
        status=TransactionStatus.PAID,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def test_budget_progress_calculates_percentage(db, sample_user, sample_account, sample_category):
    service = BudgetService(db)
    service.set_budget(
        user_id=sample_user.id,
        category_id=sample_category.id,
        month=9,
        year=2026,
        amount_limit=Decimal("800.00"),
    )
    _create_expense(
        db,
        sample_user.id,
        sample_account.id,
        sample_category.id,
        "400.00",
        date(2026, 9, 10),
    )

    progress = service.get_budget_progress(sample_user.id, 9, 2026)

    assert len(progress) == 1
    item = progress[0]
    assert item.category_id == sample_category.id
    assert item.amount_limit == Decimal("800.00")
    assert item.spent == Decimal("400.00")
    assert item.percentage == 50.0
    assert item.status == "OK"


def test_budget_progress_changes_color_thresholds(db, sample_user, sample_account, sample_category):
    service = BudgetService(db)
    service.set_budget(
        user_id=sample_user.id,
        category_id=sample_category.id,
        month=9,
        year=2026,
        amount_limit=Decimal("100.00"),
    )
    _create_expense(
        db,
        sample_user.id,
        sample_account.id,
        sample_category.id,
        "80.00",
        date(2026, 9, 1),
    )

    warning_progress = service.get_budget_progress(sample_user.id, 9, 2026)
    assert warning_progress[0].percentage == 80.0
    assert warning_progress[0].status == "WARNING"

    _create_expense(
        db,
        sample_user.id,
        sample_account.id,
        sample_category.id,
        "15.00",
        date(2026, 9, 2),
    )
    exceeded_progress = service.get_budget_progress(sample_user.id, 9, 2026)
    assert exceeded_progress[0].percentage == 95.0
    assert exceeded_progress[0].status == "EXCEEDED"


def test_budget_progress_isolates_month(db, sample_user, sample_account, sample_category):
    service = BudgetService(db)
    service.set_budget(
        user_id=sample_user.id,
        category_id=sample_category.id,
        month=9,
        year=2026,
        amount_limit=Decimal("500.00"),
    )
    _create_expense(
        db,
        sample_user.id,
        sample_account.id,
        sample_category.id,
        "300.00",
        date(2026, 8, 15),
    )
    _create_expense(
        db,
        sample_user.id,
        sample_account.id,
        sample_category.id,
        "100.00",
        date(2026, 9, 15),
    )

    progress = service.get_budget_progress(sample_user.id, 9, 2026)
    assert progress[0].spent == Decimal("100.00")
    assert progress[0].percentage == 20.0


def test_budget_progress_isolates_users(db, sample_user, sample_account, sample_category):
    other_user = User(
        name="Outro Usuário",
        email="outro-budget@email.com",
        password_hash="hash",
        is_active=True,
        is_deleted=False,
    )
    db.add(other_user)
    db.commit()
    db.refresh(other_user)

    other_category = Category(
        user_id=other_user.id,
        name="Outros Gastos",
        transaction_type=TransactionType.EXPENSE,
        is_system=False,
    )
    db.add(other_category)
    db.commit()
    db.refresh(other_category)

    service = BudgetService(db)
    service.set_budget(
        user_id=sample_user.id,
        category_id=sample_category.id,
        month=9,
        year=2026,
        amount_limit=Decimal("200.00"),
    )
    service.set_budget(
        user_id=other_user.id,
        category_id=other_category.id,
        month=9,
        year=2026,
        amount_limit=Decimal("200.00"),
    )

    _create_expense(
        db,
        sample_user.id,
        sample_account.id,
        sample_category.id,
        "100.00",
        date(2026, 9, 10),
    )
    _create_expense(
        db,
        other_user.id,
        sample_account.id,
        other_category.id,
        "150.00",
        date(2026, 9, 11),
    )

    user_progress = service.get_budget_progress(sample_user.id, 9, 2026)
    other_progress = service.get_budget_progress(other_user.id, 9, 2026)

    assert user_progress[0].spent == Decimal("100.00")
    assert other_progress[0].spent == Decimal("150.00")


def test_budget_progress_with_no_expenses_returns_zero_percent(db, sample_user, sample_category):
    service = BudgetService(db)
    service.set_budget(
        user_id=sample_user.id,
        category_id=sample_category.id,
        month=9,
        year=2026,
        amount_limit=Decimal("300.00"),
    )

    progress = service.get_budget_progress(sample_user.id, 9, 2026)
    assert progress[0].spent == Decimal("0.00")
    assert progress[0].percentage == 0.0
    assert progress[0].status == "OK"


def test_set_budget_rejects_invalid_values(db, sample_user, sample_category):
    service = BudgetService(db)
    with pytest.raises(ValueError):
        service.set_budget(
            user_id=sample_user.id,
            category_id=sample_category.id,
            month=13,
            year=2026,
            amount_limit=Decimal("100.00"),
        )
    with pytest.raises(ValueError):
        service.set_budget(
            user_id=sample_user.id,
            category_id=sample_category.id,
            month=9,
            year=2026,
            amount_limit=Decimal("0.00"),
        )


def test_set_budget_upserts_existing_budget(db, sample_user, sample_category):
    service = BudgetService(db)
    service.set_budget(
        user_id=sample_user.id,
        category_id=sample_category.id,
        month=9,
        year=2026,
        amount_limit=Decimal("500.00"),
    )
    service.set_budget(
        user_id=sample_user.id,
        category_id=sample_category.id,
        month=9,
        year=2026,
        amount_limit=Decimal("700.00"),
    )

    budgets = db.query(Budget).filter(Budget.user_id == sample_user.id).all()
    assert len(budgets) == 1
    assert budgets[0].amount_limit == Decimal("700.00")
