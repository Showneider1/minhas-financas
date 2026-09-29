"""Testes do AnalyticsService — agrupamentos no banco e isolamento por usuário."""

from datetime import date
from decimal import Decimal

import pytest
from dateutil.relativedelta import relativedelta

from database.enums import TransactionStatus, TransactionType
from database.models.account import Account
from database.models.category import Category
from database.models.transaction import Transaction
from database.models.user import User
from services.analytics_service import AnalyticsService


def _create_category(db, user_id, name, transaction_type, color):
    category = Category(
        user_id=user_id,
        name=name,
        transaction_type=transaction_type,
        icon="🏷️",
        color=color,
        is_system=False,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def _create_transaction(
    db,
    user_id,
    account_id,
    category_id,
    *,
    amount,
    transaction_type,
    reference_date,
):
    transaction = Transaction(
        user_id=user_id,
        account_id=account_id,
        category_id=category_id,
        description=f"Transação {transaction_type.value}",
        base_amount=Decimal(amount),
        transaction_type=transaction_type,
        purchase_date=reference_date,
        due_date=reference_date,
        paid_date=reference_date,
        status=TransactionStatus.PAID,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@pytest.fixture
def analytics_data(db, sample_user, sample_account):
    current_month = date.today().replace(day=1)
    previous_month = current_month - relativedelta(months=1)

    food_category = _create_category(
        db,
        sample_user.id,
        "Alimentação",
        TransactionType.EXPENSE,
        "#e74c3c",
    )
    transport_category = _create_category(
        db,
        sample_user.id,
        "Transporte",
        TransactionType.EXPENSE,
        "#e67e22",
    )
    salary_category = _create_category(
        db,
        sample_user.id,
        "Salário",
        TransactionType.INCOME,
        "#2ecc71",
    )
    transfer_category = _create_category(
        db,
        sample_user.id,
        "Transferência",
        TransactionType.TRANSFER,
        "#95a5a6",
    )

    _create_transaction(
        db,
        sample_user.id,
        sample_account.id,
        food_category.id,
        amount="100.00",
        transaction_type=TransactionType.EXPENSE,
        reference_date=current_month,
    )
    _create_transaction(
        db,
        sample_user.id,
        sample_account.id,
        transport_category.id,
        amount="50.00",
        transaction_type=TransactionType.EXPENSE,
        reference_date=current_month,
    )
    _create_transaction(
        db,
        sample_user.id,
        sample_account.id,
        salary_category.id,
        amount="300.00",
        transaction_type=TransactionType.INCOME,
        reference_date=current_month,
    )
    _create_transaction(
        db,
        sample_user.id,
        sample_account.id,
        transfer_category.id,
        amount="200.00",
        transaction_type=TransactionType.TRANSFER,
        reference_date=current_month,
    )

    _create_transaction(
        db,
        sample_user.id,
        sample_account.id,
        food_category.id,
        amount="80.00",
        transaction_type=TransactionType.EXPENSE,
        reference_date=previous_month,
    )
    _create_transaction(
        db,
        sample_user.id,
        sample_account.id,
        salary_category.id,
        amount="120.00",
        transaction_type=TransactionType.INCOME,
        reference_date=previous_month,
    )

    other_user = User(
        name="Outro Usuário",
        email="outro-analytics@email.com",
        password_hash="hash",
        is_active=True,
        is_deleted=False,
    )
    db.add(other_user)
    db.commit()
    db.refresh(other_user)

    other_account = Account(
        user_id=other_user.id,
        name="Conta Outro Usuário",
        balance=Decimal("0.00"),
        initial_balance=Decimal("0.00"),
        is_active=True,
    )
    db.add(other_account)
    db.commit()
    db.refresh(other_account)

    other_category = _create_category(
        db,
        other_user.id,
        "Outros",
        TransactionType.EXPENSE,
        "#95a5a6",
    )
    _create_transaction(
        db,
        other_user.id,
        other_account.id,
        other_category.id,
        amount="999.00",
        transaction_type=TransactionType.EXPENSE,
        reference_date=current_month,
    )

    return {
        "food_category": food_category,
        "transport_category": transport_category,
        "salary_category": salary_category,
        "transfer_category": transfer_category,
        "other_user": other_user,
    }


def test_expenses_by_category_ignores_transfer_and_other_users(db, sample_user, analytics_data):
    service = AnalyticsService(db)
    today = date.today()

    result = service.get_expenses_by_category(
        sample_user.id,
        month=today.month,
        year=today.year,
    )

    assert len(result) == 2
    assert result[0]["name"] == "Alimentação"
    assert result[0]["total"] == Decimal("100.00")
    assert result[1]["name"] == "Transporte"
    assert result[1]["total"] == Decimal("50.00")

    all_totals = sum(item["total"] for item in result)
    assert all_totals == Decimal("150.00")


def test_expenses_by_category_returns_empty_for_month_without_data(db, sample_user, analytics_data):
    service = AnalyticsService(db)

    result = service.get_expenses_by_category(
        sample_user.id,
        month=1,
        year=2030,
    )

    assert result == []


def test_cash_flow_history_excludes_transfer_and_isolates_user(db, sample_user, analytics_data):
    service = AnalyticsService(db)

    history = service.get_cash_flow_history(
        sample_user.id,
        limit_months=6,
    )

    assert len(history) == 6

    current = history[-1]
    previous = history[-2]

    assert current["income"] == Decimal("300.00")
    assert current["expenses"] == Decimal("150.00")
    assert current["net"] == Decimal("150.00")

    assert previous["income"] == Decimal("120.00")
    assert previous["expenses"] == Decimal("80.00")
    assert previous["net"] == Decimal("40.00")

    assert all(item["income"] == Decimal("0.00") for item in history[:-2])
    assert all(item["expenses"] == Decimal("0.00") for item in history[:-2])


def test_cash_flow_history_fills_months_without_movement(db, sample_user):
    service = AnalyticsService(db)

    history = service.get_cash_flow_history(
        sample_user.id,
        limit_months=3,
    )

    assert len(history) == 3
    assert all(item["income"] == Decimal("0.00") for item in history)
    assert all(item["expenses"] == Decimal("0.00") for item in history)
    assert all(item["net"] == Decimal("0.00") for item in history)


def test_invalid_period_is_rejected(db, sample_user):
    service = AnalyticsService(db)

    with pytest.raises(ValueError):
        service.get_expenses_by_category(
            sample_user.id,
            month=13,
            year=2026,
        )

    with pytest.raises(ValueError):
        service.get_cash_flow_history(
            sample_user.id,
            limit_months=0,
        )
