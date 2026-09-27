"""Parcelamento — correção matemática (Missão 2 Fase 4).

sum(parcelas) == valor_original SEMPRE, resto de centavos nas PRIMEIRAS:
100,00/3 -> [33.34, 33.33, 33.33]. Sem float (Decimal).
"""
from datetime import date
from decimal import Decimal

import pytest

from database.models.category import TransactionType
from database.models.transaction import Transaction, TransactionStatus
from services.recurrence_service import RecurrenceService


def _base(db, sample_user, sample_account, sample_category, amount, due=date(2026, 1, 10)):
    tx = Transaction(
        user_id=sample_user.id,
        description="Parcelado",
        base_amount=Decimal(str(amount)),
        transaction_type=TransactionType.EXPENSE,
        category_id=sample_category.id,
        account_id=sample_account.id,
        purchase_date=due,
        due_date=due,
        paid_date=None,
        status=TransactionStatus.PENDING,
        is_recurring=False,
        installment_number=1,
        total_installments=1,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def _all_parts(base, generated):
    return [base.base_amount] + [t.base_amount for t in generated]


def test_installments_sum_equals_base(db, sample_user, sample_account, sample_category):
    base = _base(db, sample_user, sample_account, sample_category, "1200.00")
    generated = RecurrenceService(db).generate_installments(base, total=6)
    assert len(generated) == 5
    parts = _all_parts(base, generated)
    assert len(parts) == 6
    assert sum(parts, Decimal("0.00")) == Decimal("1200.00")
    assert all(v < Decimal("1200.00") for v in parts)


def test_generate_installments_is_idempotent_guarded(
    db, sample_user, sample_account, sample_category
):
    base = _base(db, sample_user, sample_account, sample_category, "300.00",
                 due=date(2026, 2, 5))
    svc = RecurrenceService(db)
    svc.generate_installments(base, total=3)
    with pytest.raises(ValueError):
        svc.generate_installments(base, total=3)


def test_split_100_in_3_remainder_first(db, sample_user, sample_account, sample_category):
    base = _base(db, sample_user, sample_account, sample_category, "100.00")
    generated = RecurrenceService(db).generate_installments(base, total=3)
    parts = _all_parts(base, generated)
    assert parts == [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")]
    assert sum(parts, Decimal("0.00")) == Decimal("100.00")


def test_two_installments_even(db, sample_user, sample_account, sample_category):
    base = _base(db, sample_user, sample_account, sample_category, "99.99")
    generated = RecurrenceService(db).generate_installments(base, total=2)
    parts = _all_parts(base, generated)
    assert parts == [Decimal("50.00"), Decimal("49.99")]
    assert sum(parts, Decimal("0.00")) == Decimal("99.99")


def test_many_decimals_and_high_values(db, sample_user, sample_account, sample_category):
    base = _base(db, sample_user, sample_account, sample_category, "1234567.89")
    generated = RecurrenceService(db).generate_installments(base, total=12)
    parts = _all_parts(base, generated)
    assert sum(parts, Decimal("0.00")) == Decimal("1234567.89")
    assert all(p.as_tuple().exponent >= -2 for p in parts)


def test_single_installment_rejected(db, sample_user, sample_account, sample_category):
    base = _base(db, sample_user, sample_account, sample_category, "50.00")
    with pytest.raises(ValueError):
        RecurrenceService(db).generate_installments(base, total=1)


def test_negative_and_zero_split_exactly(
    db, sample_user, sample_account, sample_category
):
    # split_money é exato até para negativos (a API impede base <= 0 no schema).
    from utils.money import split_money

    assert split_money("-10.00", 2) == [Decimal("-5.00"), Decimal("-5.00")]
    assert split_money("0.00", 2) == [Decimal("0.00"), Decimal("0.00")]


def test_due_dates_advance_monthly(db, sample_user, sample_account, sample_category):
    base = _base(db, sample_user, sample_account, sample_category, "300.00",
                 due=date(2026, 1, 15))
    generated = RecurrenceService(db).generate_installments(base, total=3)
    dues = [base.due_date] + [t.due_date for t in generated]
    assert [d.isoformat() for d in dues] == ["2026-01-15", "2026-02-15", "2026-03-15"]
    nums = [base.installment_number] + [t.installment_number for t in generated]
    assert nums == [1, 2, 3]


def test_paid_base_cannot_be_parceled(db, sample_user, sample_account, sample_category):
    base = _base(db, sample_user, sample_account, sample_category, "300.00")
    base.status = TransactionStatus.PAID
    base.paid_date = date(2026, 1, 10)
    db.commit()
    with pytest.raises(ValueError):
        RecurrenceService(db).generate_installments(base, total=3)


def test_cancel_parcel_keeps_others(db, sample_user, sample_account, sample_category):
    """Cancelar (excluir) uma parcela pendente não afeta as demais."""
    from services.finance_service import FinanceService

    base = _base(db, sample_user, sample_account, sample_category, "300.00")
    generated = RecurrenceService(db).generate_installments(base, total=3)
    victim = generated[0]
    FinanceService(db).delete_transaction(victim.id, sample_user.id)
    remaining = (
        db.query(Transaction)
        .filter(Transaction.user_id == sample_user.id,
                Transaction.total_installments == 3)
        .all()
    )
    assert len(remaining) == 2
    assert sum((t.base_amount for t in remaining), Decimal("0.00")) == Decimal("200.00")
