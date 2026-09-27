"""TransferService — invariantes de transferência (Missão 2 Fase 5).

- Origem −X, destino +X, patrimônio inalterado.
- Nunca receita/despesa (KPIs zerados).
- Idempotente por client_transfer_id; auditável (grupo + vínculo).
- Isolada por usuário; validações (valor>0, contas distintas, ativas, do dono).
"""
from datetime import date
from decimal import Decimal

import pytest

from database.models.account import Account
from database.models.category import Category, TransactionType
from database.models.transaction import Transaction, TransactionStatus
from services.balance_service import BalanceService
from services.finance_service import FinanceService
from services.transfer_service import TransferService, TransferError


@pytest.fixture
def accounts(db, sample_user):
    a = Account(user_id=sample_user.id, name="Conta A",
                balance=Decimal("5000.00"), initial_balance=Decimal("5000.00"),
                is_active=True)
    b = Account(user_id=sample_user.id, name="Conta B",
                balance=Decimal("2000.00"), initial_balance=Decimal("2000.00"),
                is_active=True)
    db.add_all([a, b])
    db.commit()
    db.refresh(a)
    db.refresh(b)
    return a, b


@pytest.fixture
def transfer_category(db, sample_user):
    c = Category(user_id=sample_user.id, name="Transferência",
                 transaction_type=TransactionType.TRANSFER, is_system=False)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def test_transfer_moves_and_preserves_wealth(db, sample_user, accounts, transfer_category):
    a, b = accounts
    bal = BalanceService(db)
    before = bal.get_total_balance(sample_user.id)

    tx = TransferService(db).transfer(
        user_id=sample_user.id, from_account_id=a.id, to_account_id=b.id,
        amount=Decimal("1000.00"), paid_date=date(2026, 4, 1),
        category_id=transfer_category.id, client_transfer_id="key-001",
    )
    assert tx.transaction_type == TransactionType.TRANSFER
    assert tx.destination_account_id == b.id
    assert tx.transfer_group_id
    assert tx.client_transfer_id == "key-001"
    assert tx.status == TransactionStatus.PAID

    assert bal.get_account_balance(a.id, sample_user.id) == Decimal("4000.00")
    assert bal.get_account_balance(b.id, sample_user.id) == Decimal("3000.00")
    assert bal.get_total_balance(sample_user.id) == before


def test_transfer_excluded_from_income_expense(db, sample_user, accounts, transfer_category):
    a, b = accounts
    TransferService(db).transfer(
        user_id=sample_user.id, from_account_id=a.id, to_account_id=b.id,
        amount=Decimal("1000.00"), paid_date=date(2026, 4, 1),
        category_id=transfer_category.id, client_transfer_id="key-002",
    )
    s = BalanceService(db).get_period_summary(
        sample_user.id, date(2026, 4, 1), date(2026, 4, 30))
    assert s["income_paid"] == Decimal("0.00")
    assert s["expense_paid"] == Decimal("0.00")
    # Resumo do FinanceService também exclui.
    r = FinanceService(db).get_dashboard_summary(sample_user.id, 4, 2026)
    assert r["income"] == Decimal("0.00") and r["expense"] == Decimal("0.00")


def test_transfer_idempotent_retry(db, sample_user, accounts, transfer_category):
    a, b = accounts
    svc = TransferService(db)
    t1 = svc.transfer(user_id=sample_user.id, from_account_id=a.id, to_account_id=b.id,
                      amount=Decimal("100.00"), paid_date=date(2026, 4, 2),
                      category_id=transfer_category.id, client_transfer_id="key-003")
    t2 = svc.transfer(user_id=sample_user.id, from_account_id=a.id, to_account_id=b.id,
                      amount=Decimal("100.00"), paid_date=date(2026, 4, 2),
                      category_id=transfer_category.id, client_transfer_id="key-003")
    assert t1.id == t2.id
    assert db.query(Transaction).filter(Transaction.client_transfer_id == "key-003").count() == 1
    bal = BalanceService(db)
    assert bal.get_account_balance(a.id, sample_user.id) == Decimal("4900.00")


def test_transfer_pending_moves_nothing_until_confirm(
    db, sample_user, accounts, transfer_category
):
    a, b = accounts
    svc = TransferService(db)
    tx = svc.transfer(user_id=sample_user.id, from_account_id=a.id, to_account_id=b.id,
                      amount=Decimal("500.00"),
                      category_id=transfer_category.id, client_transfer_id="key-004")
    assert tx.status == TransactionStatus.PENDING
    bal = BalanceService(db)
    assert bal.get_account_balance(a.id, sample_user.id) == Decimal("5000.00")
    svc.confirm_transfer(tx.id, sample_user.id, paid_date=date(2026, 4, 3))
    assert bal.get_account_balance(a.id, sample_user.id) == Decimal("4500.00")
    assert bal.get_account_balance(b.id, sample_user.id) == Decimal("2500.00")


def test_transfer_validations(db, sample_user, accounts, transfer_category, sample_category):
    a, b = accounts
    svc = TransferService(db)
    with pytest.raises(TransferError):
        svc.transfer(sample_user.id, a.id, a.id, Decimal("10.00"),
                     category_id=transfer_category.id)
    with pytest.raises(TransferError):
        svc.transfer(sample_user.id, a.id, b.id, Decimal("0.00"),
                     category_id=transfer_category.id)
    with pytest.raises(TransferError):
        svc.transfer(sample_user.id, a.id, b.id, Decimal("-5.00"),
                     category_id=transfer_category.id)
    # Categoria não-TRANSFER rejeitada.
    with pytest.raises(TransferError):
        svc.transfer(sample_user.id, a.id, b.id, Decimal("10.00"),
                     category_id=sample_category.id)
    # Conta de outro usuário.
    from database.models.user import User

    other = User(name="O", email="o@ex.com", password_hash="x",
                 is_active=True, is_deleted=False)
    db.add(other)
    db.commit()
    with pytest.raises(TransferError):
        svc.transfer(other.id, a.id, b.id, Decimal("10.00"),
                     category_id=transfer_category.id)


def test_transfer_key_reuse_with_divergent_params_rejected(
    db, sample_user, accounts, transfer_category
):
    a, b = accounts
    svc = TransferService(db)
    svc.transfer(user_id=sample_user.id, from_account_id=a.id, to_account_id=b.id,
                 amount=Decimal("100.00"), paid_date=date(2026, 4, 2),
                 category_id=transfer_category.id, client_transfer_id="key-006")
    with pytest.raises(TransferError):
        svc.transfer(user_id=sample_user.id, from_account_id=a.id, to_account_id=b.id,
                     amount=Decimal("999.00"), paid_date=date(2026, 4, 2),
                     category_id=transfer_category.id, client_transfer_id="key-006")


def test_transfer_delete_recalculates_both_sides(
    db, sample_user, accounts, transfer_category
):
    a, b = accounts
    svc = TransferService(db)
    tx = svc.transfer(user_id=sample_user.id, from_account_id=a.id, to_account_id=b.id,
                      amount=Decimal("1000.00"), paid_date=date(2026, 4, 1),
                      category_id=transfer_category.id, client_transfer_id="key-005")
    FinanceService(db).delete_transaction(tx.id, sample_user.id)
    bal = BalanceService(db)
    assert bal.get_account_balance(a.id, sample_user.id) == Decimal("5000.00")
    assert bal.get_account_balance(b.id, sample_user.id) == Decimal("2000.00")


def test_finance_service_rejects_direct_transfer(db, sample_user, accounts, transfer_category):
    from schemas.transaction_schema import TransactionCreate

    with pytest.raises(ValueError):
        FinanceService(db).create_transaction(
            user_id=sample_user.id,
            transaction_data=TransactionCreate(
                description="Tentativa direta",
                base_amount=Decimal("10.00"),
                transaction_type=TransactionType.TRANSFER,
                category_id=transfer_category.id,
                account_id=accounts[0].id,
                destination_account_id=accounts[1].id,
                purchase_date=date(2026, 4, 1),
                due_date=date(2026, 4, 1),
            ),
        )
