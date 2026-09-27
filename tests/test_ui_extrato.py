"""Testes do Extrato: filtros combináveis, resumo agregado e exclusão segura."""

from contextlib import contextmanager
from datetime import date
from decimal import Decimal

import pytest

import callbacks.extrato_callbacks as extrato_callbacks
from database.enums import TransactionType
from database.models.category import Category
from database.models.transaction import Transaction
from database.models.user import User
from database.repositories.transaction_repo import TransactionRepository
from schemas.transaction_schema import TransactionCreate
from services.finance_service import FinanceService, TransactionNotFound


def _income_category(db, user):
    category = Category(
        user_id=user.id,
        name="Salário",
        transaction_type=TransactionType.INCOME,
        is_system=False,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def _create_transaction(db, user, account, category, *, amount, kind, due, paid):
    return FinanceService(db).create_transaction(
        user_id=user.id,
        transaction_data=TransactionCreate(
            description=f"Transação {kind.value}",
            base_amount=amount,
            transaction_type=kind,
            category_id=category.id,
            account_id=account.id,
            purchase_date=due,
            due_date=due,
            paid_date=paid,
            is_recurring=False,
            installment_number=1,
            total_installments=1,
            notes=None,
        ),
    )


def _patch_runtime(monkeypatch, db, user_id):
    monkeypatch.setattr(extrato_callbacks, "resolve_user", lambda *args, **kwargs: user_id)

    @contextmanager
    def session_ctx():
        yield db

    monkeypatch.setattr(extrato_callbacks, "get_db_session", session_ctx)


def test_filter_by_month_type_and_category(db, sample_user, sample_account, sample_category):
    income_category = _income_category(db, sample_user)
    current_month = date.today()
    start = current_month.replace(day=1)
    end = date(current_month.year, current_month.month, 28)
    _create_transaction(
        db,
        sample_user,
        sample_account,
        sample_category,
        amount=Decimal("100.00"),
        kind=TransactionType.EXPENSE,
        due=start,
        paid=None,
    )
    _create_transaction(
        db,
        sample_user,
        sample_account,
        income_category,
        amount=Decimal("200.00"),
        kind=TransactionType.INCOME,
        due=start,
        paid=start,
    )
    _create_transaction(
        db,
        sample_user,
        sample_account,
        sample_category,
        amount=Decimal("300.00"),
        kind=TransactionType.EXPENSE,
        due=date(current_month.year + 1, current_month.month, 10),
        paid=None,
    )

    repo = TransactionRepository(db)
    transactions, total = repo.filter_transactions(
        user_id=sample_user.id,
        start_date=start,
        end_date=end,
        transaction_type=TransactionType.EXPENSE,
        category_ids=[sample_category.id],
        account_ids=[sample_account.id],
        page=1,
        page_size=10,
    )

    assert total == 1
    assert len(transactions) == 1
    assert transactions[0].base_amount == Decimal("100.00")
    assert transactions[0].transaction_type == TransactionType.EXPENSE

    summary = repo.get_filtered_summary(
        user_id=sample_user.id,
        start_date=start,
        end_date=end,
        transaction_type=TransactionType.EXPENSE,
        status=None,
        category_ids=[sample_category.id],
        account_ids=[sample_account.id],
        search=None,
    )
    assert summary["total"] == 1
    assert summary["expense"] == Decimal("100.00")
    assert summary["income"] == Decimal("0.00")


def test_extrato_callback_applies_expense_filter(
    db, monkeypatch, sample_user, sample_account, sample_category
):
    _create_transaction(
        db,
        sample_user,
        sample_account,
        sample_category,
        amount=Decimal("100.00"),
        kind=TransactionType.EXPENSE,
        due=date.today().replace(day=1),
        paid=None,
    )
    _patch_runtime(monkeypatch, db, sample_user.id)
    today = date.today()

    result = extrato_callbacks.update_extrato(
        month=today.month,
        year=today.year,
        search=None,
        acc_id=str(sample_account.id),
        cat_id=str(sample_category.id),
        type_="EXPENSE",
        status="ALL",
        _reload=0,
        page=1,
        auth_data={"token": "teste"},
    )

    table, cards, count, pagination = result
    assert "1 lançamento(s) encontrado(s)" in count
    assert "Transação EXPENSE" in str(table)
    assert "R$ 0,00" in str(cards)
    assert "R$ 100,00" in str(cards)
    assert "R$ -100,00" in str(cards)
    assert pagination == ""


def test_extrato_callback_deletes_transaction_and_updates_reload(
    db, monkeypatch, sample_user, sample_account, sample_category
):
    transaction = _create_transaction(
        db,
        sample_user,
        sample_account,
        sample_category,
        amount=Decimal("100.00"),
        kind=TransactionType.EXPENSE,
        due=date.today(),
        paid=None,
    )
    _patch_runtime(monkeypatch, db, sample_user.id)

    result = extrato_callbacks.confirmar_del(
        1,
        transaction.id,
        {"token": "teste"},
        0,
    )

    remaining = db.query(Transaction).filter(Transaction.id == transaction.id).first()
    assert remaining is None
    assert result[0] is False
    assert result[1] == 1
    assert result[2] is True
    assert result[3] == "Lançamento excluído."


def test_delete_transaction_rejects_cross_user(db, sample_user, sample_account, sample_category):
    transaction = _create_transaction(
        db,
        sample_user,
        sample_account,
        sample_category,
        amount=Decimal("100.00"),
        kind=TransactionType.EXPENSE,
        due=date.today(),
        paid=None,
    )
    other_user = User(
        name="Outro Usuário",
        email="outro@email.com",
        password_hash="hashed_password",
        is_active=True,
        is_deleted=False,
    )
    db.add(other_user)
    db.commit()
    db.refresh(other_user)

    with pytest.raises(TransactionNotFound):
        FinanceService(db).delete_transaction(transaction.id, other_user.id)

    assert db.query(Transaction).filter(Transaction.id == transaction.id).first() is not None
