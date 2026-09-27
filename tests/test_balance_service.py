"""BalanceService — regra única de saldo (Missão 2 Fases 5/6).

saldo = initial + INCOME pagos − EXPENSE pagos (+TRANSFER destino −TRANSFER origem)
TRANSFER nunca em receita/despesa; patrimônio = soma das contas ativas.
"""

from datetime import date
from decimal import Decimal

import pytest

from database.models.category import Category, TransactionType
from schemas.transaction_schema import TransactionCreate
from services.balance_service import BalanceService
from services.finance_service import FinanceService


def _category_for(db, user_id, type_):
    cat = Category(
        user_id=user_id, name=f"Cat {type_.value}", transaction_type=type_, is_system=False
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def _tx(db, user_id, acc_id, cat_id, type_, amount, paid=True):
    day = date(2026, 3, 10)
    return FinanceService(db).create_transaction(
        user_id=user_id,
        transaction_data=TransactionCreate(
            description=f"{type_.value} {amount}",
            base_amount=Decimal(str(amount)),
            transaction_type=type_,
            category_id=cat_id,
            account_id=acc_id,
            purchase_date=day,
            due_date=day,
            paid_date=day if paid else None,
        ),
    )


def test_balance_formula_initial_plus_flows(db, sample_user, sample_account, sample_category):
    bal = BalanceService(db)
    # initial 5000 (conftest) — sem lançamentos, saldo == initial.
    assert bal.get_account_balance(sample_account.id, sample_user.id) == Decimal("5000.00")
    _tx(
        db,
        sample_user.id,
        sample_account.id,
        sample_category.id,
        TransactionType.EXPENSE,
        "1500.00",
        paid=True,
    )
    assert bal.get_account_balance(sample_account.id, sample_user.id) == Decimal("3500.00")
    # Pendente não move saldo.
    _tx(
        db,
        sample_user.id,
        sample_account.id,
        sample_category.id,
        TransactionType.EXPENSE,
        "999.99",
        paid=False,
    )
    assert bal.get_account_balance(sample_account.id, sample_user.id) == Decimal("3500.00")


def test_total_balance_sums_active_accounts(db, sample_user, sample_account):
    from database.models.account import Account

    other = Account(
        user_id=sample_user.id,
        name="Poupança",
        balance=Decimal("0"),
        initial_balance=Decimal("100.00"),
        is_active=True,
    )
    db.add(other)
    db.commit()
    bal = BalanceService(db)
    assert bal.get_total_balance(sample_user.id) == Decimal("5100.00")


def test_reconcile_detects_and_heals_drift(db, sample_user, sample_account, sample_category):
    bal = BalanceService(db)
    _tx(
        db,
        sample_user.id,
        sample_account.id,
        sample_category.id,
        TransactionType.EXPENSE,
        "10.00",
        paid=True,
    )
    # Simula cache stale (legado nunca atualizava Account.balance).
    sample_account.balance = Decimal("0.00")
    db.commit()
    report = bal.reconcile(sample_user.id)
    assert report["ok"] is False
    assert report["divergences"][0]["account_id"] == sample_account.id
    bal.recalculate_and_persist(sample_account.id, sample_user.id, commit=True)
    assert bal.reconcile(sample_user.id)["ok"] is True


def test_period_summary_paid_vs_pending(db, sample_user, sample_account, sample_category):
    bal = BalanceService(db)
    inc_cat = _category_for(db, sample_user.id, TransactionType.INCOME)
    _tx(
        db,
        sample_user.id,
        sample_account.id,
        inc_cat.id,
        TransactionType.INCOME,
        "2000.00",
        paid=True,
    )
    _tx(
        db,
        sample_user.id,
        sample_account.id,
        sample_category.id,
        TransactionType.EXPENSE,
        "500.00",
        paid=False,
    )
    s = bal.get_period_summary(sample_user.id, date(2026, 3, 1), date(2026, 3, 31))
    assert s["income_paid"] == Decimal("2000.00")
    assert s["expense_paid"] == Decimal("0.00")
    assert s["balance_paid"] == Decimal("2000.00")
    assert s["expense_pending"] == Decimal("500.00")
    assert s["balance_forecast"] == Decimal("1500.00")


def test_cross_user_balance_denied(db, sample_user, sample_account):
    from database.models.user import User

    other = User(
        name="Outro", email="outro@ex.com", password_hash="x", is_active=True, is_deleted=False
    )
    db.add(other)
    db.commit()
    with pytest.raises(LookupError):
        BalanceService(db).get_account_balance(sample_account.id, other.id)
