"""Contrato canônico de Transaction (Missão 2 Fase 2).

- base_amount é o ÚNICO valor; sem amount/interest/discount/cashback.
- Pago ≡ status PAID + paid_date; mark_as_paid sincroniza e é idempotente.
- delete_transaction com dono; update parcial via TransactionUpdate.
- Estorno: voltar para PENDING remove do saldo.
"""
from datetime import date
from decimal import Decimal

import pytest

from database.models.category import TransactionType
from database.models.transaction import Transaction, TransactionStatus
from schemas.transaction_schema import TransactionCreate, TransactionUpdate
from services.balance_service import BalanceService
from services.finance_service import FinanceService, TransactionNotFound


def _create(db, uid, acc, cat, amount="100.00", paid=True, type_=TransactionType.EXPENSE):
    day = date(2026, 5, 10)
    return FinanceService(db).create_transaction(
        user_id=uid,
        transaction_data=TransactionCreate(
            description="Contrato",
            base_amount=Decimal(amount),
            transaction_type=type_,
            category_id=cat,
            account_id=acc,
            purchase_date=day,
            due_date=day,
            paid_date=day if paid else None,
        ),
    )


def test_no_amount_columns_on_model():
    assert not hasattr(Transaction, "amount")
    assert not hasattr(Transaction, "interest")
    assert not hasattr(Transaction, "discount")
    assert not hasattr(Transaction, "cashback")
    assert hasattr(Transaction, "base_amount")


def test_create_syncs_status_and_moves_balance(
    db, sample_user, sample_account, sample_category
):
    tx = _create(db, sample_user.id, sample_account.id, sample_category.id)
    assert tx.status == TransactionStatus.PAID
    assert isinstance(tx.base_amount, Decimal)
    bal = BalanceService(db).get_account_balance(sample_account.id, sample_user.id)
    assert bal == Decimal("5000.00") - Decimal("100.00")


def test_mark_as_paid_syncs_and_idempotent(
    db, sample_user, sample_account, sample_category
):
    tx = _create(db, sample_user.id, sample_account.id, sample_category.id, paid=False)
    assert tx.status == TransactionStatus.PENDING
    svc = FinanceService(db)
    done = svc.mark_as_paid(tx.id, sample_user.id, paid_date=date(2026, 5, 11))
    assert done.status == TransactionStatus.PAID
    assert done.paid_date == date(2026, 5, 11)
    again = svc.mark_as_paid(tx.id, sample_user.id)
    assert again.id == done.id


def test_reversal_removes_from_balance(db, sample_user, sample_account, sample_category):
    svc = FinanceService(db)
    tx = _create(db, sample_user.id, sample_account.id, sample_category.id)
    svc.update_transaction(
        tx.id, sample_user.id, TransactionUpdate(paid_date=None))
    db.refresh(tx)
    assert tx.status == TransactionStatus.PENDING
    bal = BalanceService(db).get_account_balance(sample_account.id, sample_user.id)
    assert bal == Decimal("5000.00")


def test_cancelled_cannot_be_paid(db, sample_user, sample_account, sample_category):
    tx = _create(db, sample_user.id, sample_account.id, sample_category.id)
    tx.status = TransactionStatus.CANCELLED
    tx.paid_date = None
    db.commit()
    with pytest.raises(ValueError):
        FinanceService(db).mark_as_paid(tx.id, sample_user.id)


def test_category_type_mismatch_rejected(
    db, sample_user, sample_account, sample_category
):
    from database.models.category import Category

    other_cat = Category(user_id=sample_user.id, name="Salário",
                         transaction_type=TransactionType.INCOME, is_system=False)
    db.add(other_cat)
    db.commit()
    day = date(2026, 5, 10)
    with pytest.raises(ValueError):
        FinanceService(db).create_transaction(
            user_id=sample_user.id,
            transaction_data=TransactionCreate(
                description="Receita com categoria despesa?",
                base_amount=Decimal("10.00"),
                transaction_type=TransactionType.EXPENSE,
                category_id=other_cat.id,
                account_id=sample_account.id,
                purchase_date=day,
                due_date=day,
                paid_date=day,
            ),
        )


def test_delete_unknown_or_foreign_raises(
    db, sample_user, sample_account, sample_category
):
    svc = FinanceService(db)
    with pytest.raises(TransactionNotFound):
        svc.delete_transaction(999999, sample_user.id)
    tx = _create(db, sample_user.id, sample_account.id, sample_category.id)
    from database.models.user import User

    other = User(name="X", email="x@ex.com", password_hash="h",
                 is_active=True, is_deleted=False)
    db.add(other)
    db.commit()
    with pytest.raises(TransactionNotFound):
        svc.delete_transaction(tx.id, other.id)
    with pytest.raises(TransactionNotFound):
        svc.update_transaction(tx.id, other.id, TransactionUpdate(description="Golpe financeiro aqui!"))
