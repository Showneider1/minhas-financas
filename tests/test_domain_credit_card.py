"""Domínio de Cartão de Crédito — fatura, parcelas e limite."""

from datetime import date
from decimal import Decimal

import pytest

from database.enums import TransactionStatus, TransactionType
from database.models.account import Account, AccountType
from database.models.transaction import Transaction
from services.balance_service import BalanceService
from services.credit_card_service import CreditCardError, CreditCardService


@pytest.fixture
def credit_card(db, sample_user):
    return CreditCardService(db).create_credit_card(
        user_id=sample_user.id,
        name="Nubank",
        credit_limit=Decimal("5000.00"),
        closing_day=3,
        due_day=10,
    )


def test_installment_purchase_generates_exact_amounts_and_consumes_limit(
    db, sample_user, sample_category, credit_card
):
    service = CreditCardService(db)
    balance_before = BalanceService(db).get_total_balance(sample_user.id)

    transactions = service.register_purchase(
        user_id=sample_user.id,
        credit_card_id=credit_card.id,
        amount=Decimal("1200.00"),
        purchase_date=date(2026, 10, 1),
        description="Notebook",
        category_id=sample_category.id,
        installments=3,
    )

    assert len(transactions) == 3
    assert [t.base_amount for t in transactions] == [
        Decimal("400.00"),
        Decimal("400.00"),
        Decimal("400.00"),
    ]
    assert [t.installment_number for t in transactions] == [1, 2, 3]
    assert all(t.total_installments == 3 for t in transactions)
    assert all(t.status == TransactionStatus.PENDING for t in transactions)
    assert all(t.paid_date is None for t in transactions)
    assert all(t.transaction_type == TransactionType.EXPENSE for t in transactions)
    assert all(t.credit_card_id == credit_card.id for t in transactions)

    assert service.get_available_limit(sample_user.id, credit_card.id) == Decimal("3800.00")

    balance_after = BalanceService(db).get_total_balance(sample_user.id)
    assert balance_after == balance_before


def test_installment_split_handles_exact_remainder(db, sample_user, sample_category, credit_card):
    service = CreditCardService(db)

    transactions = service.register_purchase(
        user_id=sample_user.id,
        credit_card_id=credit_card.id,
        amount=Decimal("100.00"),
        purchase_date=date(2026, 10, 1),
        description="Dízima",
        category_id=sample_category.id,
        installments=3,
    )

    values = [t.base_amount for t in transactions]
    assert values == [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]
    assert sum(values) == Decimal("100.00")
    assert service.get_available_limit(sample_user.id, credit_card.id) == Decimal("4900.00")


def test_closing_day_routes_purchase_to_correct_invoice(
    db, sample_user, sample_category, credit_card
):
    service = CreditCardService(db)

    before_closing = service.register_purchase(
        user_id=sample_user.id,
        credit_card_id=credit_card.id,
        amount=Decimal("100.00"),
        purchase_date=date(2026, 10, 2),
        description="Antes do fechamento",
        category_id=sample_category.id,
        installments=1,
    )
    on_closing = service.register_purchase(
        user_id=sample_user.id,
        credit_card_id=credit_card.id,
        amount=Decimal("200.00"),
        purchase_date=date(2026, 10, 3),
        description="No fechamento",
        category_id=sample_category.id,
        installments=1,
    )

    assert before_closing[0].due_date == date(2026, 10, 10)
    assert on_closing[0].due_date == date(2026, 11, 10)


def test_purchase_on_day_after_closing_goes_to_next_invoice(
    db, sample_user, sample_category, credit_card
):
    service = CreditCardService(db)

    transactions = service.register_purchase(
        user_id=sample_user.id,
        credit_card_id=credit_card.id,
        amount=Decimal("300.00"),
        purchase_date=date(2026, 10, 4),
        description="Depois do fechamento",
        category_id=sample_category.id,
        installments=1,
    )

    assert transactions[0].due_date == date(2026, 11, 10)


def test_invalid_purchase_is_rejected_and_persists_nothing(
    db, sample_user, sample_category, credit_card
):
    service = CreditCardService(db)

    with pytest.raises(CreditCardError):
        service.register_purchase(
            user_id=sample_user.id,
            credit_card_id=credit_card.id,
            amount=Decimal("0.00"),
            purchase_date=date(2026, 10, 1),
            description="Compra inválida",
            category_id=sample_category.id,
            installments=1,
        )

    assert db.query(Transaction).filter(Transaction.credit_card_id == credit_card.id).count() == 0
    assert service.get_available_limit(sample_user.id, credit_card.id) == Decimal("5000.00")


def test_get_invoice_returns_cycle_transactions_and_totals(
    db, sample_user, sample_category, credit_card
):
    service = CreditCardService(db)

    service.register_purchase(
        user_id=sample_user.id,
        credit_card_id=credit_card.id,
        amount=Decimal("1200.00"),
        purchase_date=date(2030, 9, 4),
        description="Notebook",
        category_id=sample_category.id,
        installments=3,
    )

    invoice = service.get_invoice(
        user_id=sample_user.id,
        credit_card_id=credit_card.id,
        month=10,
        year=2030,
    )

    assert len(invoice["transactions"]) == 1
    assert invoice["transactions"][0].base_amount == Decimal("400.00")
    assert invoice["total"] == Decimal("400.00")
    assert invoice["unpaid_total"] == Decimal("400.00")
    assert invoice["future_total"] == Decimal("800.00")
    assert invoice["status"] == "Aberta"
    assert invoice["due_date"] == date(2030, 10, 10)
    assert invoice["closing_date"] == date(2030, 10, 3)
    assert invoice["available_limit"] == Decimal("3800.00")


def test_pay_invoice_restores_limit_and_debits_source_account(
    db, sample_user, sample_category, sample_account, credit_card
):
    service = CreditCardService(db)

    service.register_purchase(
        user_id=sample_user.id,
        credit_card_id=credit_card.id,
        amount=Decimal("1200.00"),
        purchase_date=date(2030, 9, 4),
        description="Notebook",
        category_id=sample_category.id,
        installments=3,
    )

    assert service.get_available_limit(sample_user.id, credit_card.id) == Decimal("3800.00")

    payment = service.pay_invoice(
        user_id=sample_user.id,
        credit_card_id=credit_card.id,
        month=10,
        year=2030,
        source_account_id=sample_account.id,
        payment_date=date(2030, 10, 10),
    )

    assert payment.base_amount == Decimal("400.00")
    assert payment.transaction_type == TransactionType.TRANSFER
    assert payment.account_id == sample_account.id
    assert payment.destination_account_id == credit_card.account_id
    assert payment.status == TransactionStatus.PAID
    assert payment.paid_date == date(2030, 10, 10)

    assert service.get_available_limit(sample_user.id, credit_card.id) == Decimal("4200.00")

    balances = BalanceService(db)
    assert balances.get_account_balance(sample_account.id, sample_user.id) == Decimal("4600.00")
    assert balances.get_account_balance(credit_card.account_id, sample_user.id) == Decimal("0.00")

    paid_invoice = service.get_invoice(
        user_id=sample_user.id,
        credit_card_id=credit_card.id,
        month=10,
        year=2030,
    )
    assert paid_invoice["status"] == "Paga"
    assert paid_invoice["unpaid_total"] == Decimal("0.00")
    assert all(
        transaction.paid_date == date(2030, 10, 10) for transaction in paid_invoice["transactions"]
    )


def test_pay_invoice_rejects_paying_an_already_paid_invoice(
    db, sample_user, sample_category, sample_account, credit_card
):
    service = CreditCardService(db)

    service.register_purchase(
        user_id=sample_user.id,
        credit_card_id=credit_card.id,
        amount=Decimal("400.00"),
        purchase_date=date(2030, 9, 4),
        description="Cadeira",
        category_id=sample_category.id,
        installments=1,
    )

    service.pay_invoice(
        user_id=sample_user.id,
        credit_card_id=credit_card.id,
        month=10,
        year=2030,
        source_account_id=sample_account.id,
        payment_date=date(2030, 10, 10),
    )

    with pytest.raises(CreditCardError):
        service.pay_invoice(
            user_id=sample_user.id,
            credit_card_id=credit_card.id,
            month=10,
            year=2030,
            source_account_id=sample_account.id,
            payment_date=date(2030, 10, 11),
        )

    assert service.get_available_limit(sample_user.id, credit_card.id) == Decimal("5000.00")


def test_pay_invoice_rejects_insufficient_balance(db, sample_user, sample_category, credit_card):
    service = CreditCardService(db)

    low_balance_account = Account(
        user_id=sample_user.id,
        name="Conta Baixa",
        account_type=AccountType.CHECKING,
        balance=Decimal("100.00"),
        initial_balance=Decimal("100.00"),
        is_active=True,
    )
    db.add(low_balance_account)
    db.commit()
    db.refresh(low_balance_account)

    service.register_purchase(
        user_id=sample_user.id,
        credit_card_id=credit_card.id,
        amount=Decimal("400.00"),
        purchase_date=date(2030, 9, 4),
        description="Monitor",
        category_id=sample_category.id,
        installments=1,
    )

    with pytest.raises(CreditCardError):
        service.pay_invoice(
            user_id=sample_user.id,
            credit_card_id=credit_card.id,
            month=10,
            year=2030,
            source_account_id=low_balance_account.id,
            payment_date=date(2030, 10, 10),
        )

    assert service.get_available_limit(sample_user.id, credit_card.id) == Decimal("4600.00")
    assert BalanceService(db).get_account_balance(
        low_balance_account.id, sample_user.id
    ) == Decimal("100.00")
