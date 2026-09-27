"""Testes da exportação CSV do Extrato."""

from contextlib import contextmanager
from datetime import date
from decimal import Decimal

import callbacks.extrato_callbacks as extrato_callbacks
from database.enums import TransactionType
from database.models.account import Account
from database.models.category import Category
from database.models.user import User
from schemas.transaction_schema import TransactionCreate
from services.finance_service import FinanceService
from utils.exceptions import AuthenticationError


def _patch_runtime(monkeypatch, db, user_id):
    monkeypatch.setattr(extrato_callbacks, "resolve_user", lambda *a, **kw: user_id)

    @contextmanager
    def session_ctx():
        yield db

    monkeypatch.setattr(extrato_callbacks, "get_db_session", session_ctx)


def _create_transaction(db, user, account, category, *, description, amount, kind, due, paid):
    return FinanceService(db).create_transaction(
        user_id=user.id,
        transaction_data=TransactionCreate(
            description=description,
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


def _create_other_user_with_transaction(db):
    other = User(
        name="Outro Usuario",
        email="outro-usuarios@email.com",
        password_hash="hash",
        is_active=True,
        is_deleted=False,
    )
    db.add(other)
    db.commit()
    db.refresh(other)

    other_account = Account(
        user_id=other.id,
        name="Conta Outro",
        balance=Decimal("1000.00"),
        initial_balance=Decimal("1000.00"),
        is_active=True,
    )
    other_category = Category(
        user_id=other.id,
        name="Outros Gastos",
        transaction_type=TransactionType.EXPENSE,
        is_system=False,
    )
    db.add_all([other_account, other_category])
    db.commit()
    db.refresh(other_account)
    db.refresh(other_category)

    _create_transaction(
        db,
        other,
        other_account,
        other_category,
        description="Transacao de Outro Usuario",
        amount=Decimal("777.00"),
        kind=TransactionType.EXPENSE,
        due=date.today().replace(day=1),
        paid=None,
    )


def test_export_csv_callback_returns_download(
    db, monkeypatch, sample_user, sample_account, sample_category
):
    _create_transaction(
        db,
        sample_user,
        sample_account,
        sample_category,
        description="Supermercado",
        amount=Decimal("123.45"),
        kind=TransactionType.EXPENSE,
        due=date.today().replace(day=1),
        paid=None,
    )
    _patch_runtime(monkeypatch, db, sample_user.id)
    today = date.today()

    result = extrato_callbacks.exportar_extrato_csv(
        1,
        today.month,
        today.year,
        None,
        str(sample_account.id),
        str(sample_category.id),
        "EXPENSE",
        "ALL",
        {"token": "teste"},
    )

    assert isinstance(result, dict)
    assert result["filename"] == f"extrato_{today.year}-{today.month:02d}.csv"
    assert "Supermercado" in result["content"]
    assert "123,45" in result["content"]


def test_export_csv_callback_filters_by_user(
    db, monkeypatch, sample_user, sample_account, sample_category
):
    _create_transaction(
        db,
        sample_user,
        sample_account,
        sample_category,
        description="Supermercado",
        amount=Decimal("123.45"),
        kind=TransactionType.EXPENSE,
        due=date.today().replace(day=1),
        paid=None,
    )
    _create_other_user_with_transaction(db)
    _patch_runtime(monkeypatch, db, sample_user.id)
    today = date.today()

    result = extrato_callbacks.exportar_extrato_csv(
        1,
        today.month,
        today.year,
        None,
        None,
        None,
        "ALL",
        "ALL",
        {"token": "teste"},
    )

    assert "Supermercado" in result["content"]
    assert "Transacao de Outro Usuario" not in result["content"]


def test_export_csv_callback_requires_authentication(db, monkeypatch):
    monkeypatch.setattr(
        extrato_callbacks,
        "resolve_user",
        lambda *a, **kw: (_ for _ in ()).throw(AuthenticationError("Sessão inválida")),
    )

    today = date.today()
    result = extrato_callbacks.exportar_extrato_csv(
        1,
        today.month,
        today.year,
        None,
        None,
        None,
        "ALL",
        "ALL",
        {},
    )

    assert result is None
