"""Banco — CRUD, integridade referencial e schema (Missão 2 Fases 10/12).

- init_db cria TODAS as tabelas (goals, scheduled_bills, reset tokens).
- Contas/categorias: criação, soft-delete, unicidade, bloqueio em uso.
- Transação órfã (conta/categoria de outro usuário) é rejeitada no service.
"""

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from database.base import Base
from database.models.account import AccountType
from database.models.category import TransactionType
from schemas.account_schema import AccountCreate
from schemas.category_schema import CategoryCreate
from schemas.transaction_schema import TransactionCreate
from services.account_service import AccountService
from services.category_service import CategoryService
from services.finance_service import FinanceService, TransactionNotFound


def test_init_db_creates_all_tables(db_engine):
    tables = set(Base.metadata.tables.keys())
    for expected in (
        "users",
        "accounts",
        "categories",
        "transactions",
        "budgets",
        "goals",
        "scheduled_bills",
        "assets",
        "investment_operations",
        "password_reset_tokens",
    ):
        assert expected in tables, f"tabela ausente no metadata: {expected}"


def test_account_crud_soft_delete(db, sample_user):
    svc = AccountService(db)
    acc = svc.create_account(
        sample_user.id,
        AccountCreate(
            name="Reserva", account_type=AccountType.SAVINGS, initial_balance=Decimal("100.00")
        ),
    )
    assert acc.balance == Decimal("100.00")
    assert svc.get_account_by_id(acc.id, sample_user.id) is not None
    assert svc.delete_account(acc.id, sample_user.id) is True
    assert svc.get_account_by_id(acc.id, sample_user.id) is None
    assert svc.get_user_accounts(sample_user.id) == []


def test_account_with_transactions_cannot_be_deleted(
    db, sample_user, sample_account, sample_category
):
    from datetime import date

    FinanceService(db).create_transaction(
        user_id=sample_user.id,
        transaction_data=TransactionCreate(
            description="Uso da conta",
            base_amount=Decimal("10.00"),
            transaction_type=TransactionType.EXPENSE,
            category_id=sample_category.id,
            account_id=sample_account.id,
            purchase_date=date(2026, 6, 1),
            due_date=date(2026, 6, 1),
            paid_date=date(2026, 6, 1),
        ),
    )
    with pytest.raises(ValueError):
        AccountService(db).delete_account(sample_account.id, sample_user.id)


def test_category_unique_per_user(db, sample_user):
    svc = CategoryService(db)
    svc.create_category(sample_user.id, CategoryCreate(name="Cinema", type=TransactionType.EXPENSE))
    with pytest.raises(IntegrityError):
        svc.create_category(
            sample_user.id, CategoryCreate(name="Cinema", type=TransactionType.EXPENSE)
        )


def test_category_in_use_cannot_be_deleted(db, sample_user, sample_account, sample_category):
    from datetime import date

    FinanceService(db).create_transaction(
        user_id=sample_user.id,
        transaction_data=TransactionCreate(
            description="Amarra categoria",
            base_amount=Decimal("10.00"),
            transaction_type=TransactionType.EXPENSE,
            category_id=sample_category.id,
            account_id=sample_account.id,
            purchase_date=date(2026, 6, 1),
            due_date=date(2026, 6, 1),
            paid_date=date(2026, 6, 1),
        ),
    )
    with pytest.raises(ValueError):
        CategoryService(db).delete_category(sample_category.id, sample_user.id)


def test_transaction_with_foreign_account_rejected(
    db, sample_user, sample_account, sample_category
):
    from datetime import date

    from database.models.user import User

    other = User(
        name="Estranho",
        email="estranho@ex.com",
        password_hash="h",
        is_active=True,
        is_deleted=False,
    )
    db.add(other)
    db.commit()
    with pytest.raises(TransactionNotFound):
        FinanceService(db).create_transaction(
            user_id=other.id,
            transaction_data=TransactionCreate(
                description="Conta alheia",
                base_amount=Decimal("10.00"),
                transaction_type=TransactionType.EXPENSE,
                category_id=sample_category.id,
                account_id=sample_account.id,  # conta do sample_user!
                purchase_date=date(2026, 6, 1),
                due_date=date(2026, 6, 1),
            ),
        )


def test_category_system_cannot_be_deleted(db, sample_user, sample_category):
    sample_category.is_system = True
    db.commit()
    with pytest.raises(ValueError):
        CategoryService(db).delete_category(sample_category.id, sample_user.id)
