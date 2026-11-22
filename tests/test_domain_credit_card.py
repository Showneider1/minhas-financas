"""Domínio de Cartão de Crédito — fatura, parcelas e limite."""

import hashlib
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


def _invoice_key(user_id: int, card_id: int, month: int, year: int) -> str:
    return (
        "inv:" + hashlib.sha256(f"{user_id}:{card_id}:{month:02d}:{year}".encode()).hexdigest()[:32]
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


def test_pay_invoice_idempotency_key_and_single_debit(
    db, sample_user, sample_category, sample_account, credit_card
):
    """Chave determinística resolve corrida; chamada sequencial duplicada ainda falha."""
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

    balance_before = BalanceService(db).get_account_balance(sample_account.id, sample_user.id)

    payment = service.pay_invoice(
        user_id=sample_user.id,
        credit_card_id=credit_card.id,
        month=10,
        year=2030,
        source_account_id=sample_account.id,
        payment_date=date(2030, 10, 10),
    )

    expected_key = (
        "inv:"
        + hashlib.sha256(f"{sample_user.id}:{credit_card.id}:10:2030".encode()).hexdigest()[:32]
    )
    assert payment.client_transfer_id == expected_key
    assert len(payment.client_transfer_id) == 36

    with pytest.raises(CreditCardError):
        service.pay_invoice(
            user_id=sample_user.id,
            credit_card_id=credit_card.id,
            month=10,
            year=2030,
            source_account_id=sample_account.id,
            payment_date=date(2030, 10, 11),
        )

    payment_transfers = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == sample_user.id,
            Transaction.transaction_type == TransactionType.TRANSFER,
            Transaction.destination_account_id == credit_card.account_id,
            Transaction.notes == f"payment_invoice:card:{credit_card.id}:month:10:year:2030",
        )
        .all()
    )
    assert len(payment_transfers) == 1
    assert payment_transfers[0].id == payment.id

    assert BalanceService(db).get_account_balance(
        sample_account.id, sample_user.id
    ) == balance_before - Decimal("400.00")
    db.refresh(sample_account)
    assert sample_account.balance == balance_before - Decimal("400.00")


def test_pay_invoice_rejects_divergent_idempotency_winner(
    db, sample_user, sample_category, sample_account, credit_card
):
    """Winner com valor/conta divergentes nunca é devolvido como fatura paga."""
    service = CreditCardService(db)
    client_key = _invoice_key(sample_user.id, credit_card.id, 10, 2030)

    planted = Transaction(
        user_id=sample_user.id,
        description="Pagamento divergente plantado",
        base_amount=Decimal("999.00"),
        transaction_type=TransactionType.TRANSFER,
        account_id=sample_account.id,
        destination_account_id=credit_card.account_id,
        category_id=service._transfer_category(sample_user.id).id,
        purchase_date=date(2030, 10, 10),
        due_date=date(2030, 10, 10),
        paid_date=date(2030, 10, 10),
        status=TransactionStatus.PAID,
        client_transfer_id=client_key,
    )
    db.add(planted)
    db.commit()
    db.refresh(planted)

    service.register_purchase(
        user_id=sample_user.id,
        credit_card_id=credit_card.id,
        amount=Decimal("400.00"),
        purchase_date=date(2030, 9, 4),
        description="Cadeira",
        category_id=sample_category.id,
        installments=1,
    )

    with pytest.raises(CreditCardError, match="Chave de idempotência reutilizada"):
        service.pay_invoice(
            user_id=sample_user.id,
            credit_card_id=credit_card.id,
            month=10,
            year=2030,
            source_account_id=sample_account.id,
            payment_date=date(2030, 10, 10),
        )

    assert db.query(Transaction).filter(Transaction.client_transfer_id == client_key).count() == 1
    assert (
        db.query(Transaction)
        .filter(
            Transaction.user_id == sample_user.id,
            Transaction.transaction_type == TransactionType.TRANSFER,
            Transaction.notes == f"payment_invoice:card:{credit_card.id}:month:10:year:2030",
        )
        .count()
        == 0
    )


def test_pay_invoice_winner_with_pending_purchase_is_rejected(
    db, sample_user, sample_category, sample_account, credit_card
):
    """Winner de parâmetros íntegros, mas com pendência no ciclo, não é devolvido."""
    service = CreditCardService(db)
    client_key = _invoice_key(sample_user.id, credit_card.id, 10, 2030)
    payment_notes = f"payment_invoice:card:{credit_card.id}:month:10:year:2030"

    winner = Transaction(
        user_id=sample_user.id,
        description=f"Pagamento da fatura {credit_card.name} — 10/2030",
        base_amount=Decimal("400.00"),
        transaction_type=TransactionType.TRANSFER,
        account_id=sample_account.id,
        destination_account_id=credit_card.account_id,
        category_id=service._transfer_category(sample_user.id).id,
        purchase_date=date(2030, 10, 10),
        due_date=date(2030, 10, 10),
        paid_date=date(2030, 10, 10),
        status=TransactionStatus.PAID,
        notes=payment_notes,
        client_transfer_id=client_key,
    )
    db.add(winner)
    db.commit()
    db.refresh(winner)

    service.register_purchase(
        user_id=sample_user.id,
        credit_card_id=credit_card.id,
        amount=Decimal("400.00"),
        purchase_date=date(2030, 9, 4),
        description="Cadeira",
        category_id=sample_category.id,
        installments=1,
    )

    with pytest.raises(CreditCardError, match="parcialmente paga"):
        service.pay_invoice(
            user_id=sample_user.id,
            credit_card_id=credit_card.id,
            month=10,
            year=2030,
            source_account_id=sample_account.id,
            payment_date=date(2030, 10, 10),
        )

    # Nenhum segundo pagamento foi criado.
    assert db.query(Transaction).filter(Transaction.client_transfer_id == client_key).count() == 1
    assert (
        db.query(Transaction)
        .filter(
            Transaction.user_id == sample_user.id,
            Transaction.transaction_type == TransactionType.TRANSFER,
            Transaction.notes == payment_notes,
        )
        .count()
        == 1
    )


def test_pay_invoice_detects_late_same_value_purchase(
    db, sample_user, sample_category, sample_account, credit_card
):
    """Compra tardia de mesmo valor não pode ser dada por paga via winner."""
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

    late = service.register_purchase(
        user_id=sample_user.id,
        credit_card_id=credit_card.id,
        amount=Decimal("400.00"),
        purchase_date=date(2030, 9, 5),
        description="Cadeira tardia",
        category_id=sample_category.id,
        installments=1,
    )
    # Garante que o cenário exercita a validação de estado, não o guard "já paga".
    assert late[0].due_date == date(2030, 10, 10)
    assert late[0].paid_date is None

    with pytest.raises(CreditCardError, match="parcialmente paga"):
        service.pay_invoice(
            user_id=sample_user.id,
            credit_card_id=credit_card.id,
            month=10,
            year=2030,
            source_account_id=sample_account.id,
            payment_date=date(2030, 10, 11),
        )


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


def test_get_user_cards_exclui_cartao_com_conta_soft_deletada(db, sample_user, credit_card):
    service = CreditCardService(db)

    cards = service.get_user_cards(sample_user.id)
    assert [c.id for c in cards] == [credit_card.id]

    anchor = db.get(Account, credit_card.account_id)
    anchor.is_deleted = True
    db.commit()

    assert service.get_user_cards(sample_user.id) == []
