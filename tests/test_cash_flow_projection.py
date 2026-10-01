"""Testes do motor de projeção de fluxo de caixa."""

from datetime import date, timedelta
from decimal import Decimal

from database.enums import (
    BillRecurrence,
    BillStatus,
    BillType,
    TransactionStatus,
    TransactionType,
)
from database.models.account import Account
from database.models.credit_card import CreditCard
from database.models.scheduled_bill import ScheduledBill
from database.models.transaction import Transaction
from services.cash_flow_projection_service import CashFlowProjectionService


def _create_pending_transaction(
    db,
    user_id,
    account_id,
    category_id,
    *,
    amount,
    due_date,
    transaction_type,
    credit_card_id=None,
):
    transaction = Transaction(
        user_id=user_id,
        account_id=account_id,
        category_id=category_id,
        description="Transação de projeção",
        base_amount=Decimal(amount),
        transaction_type=transaction_type,
        purchase_date=date.today(),
        due_date=due_date,
        paid_date=None,
        status=TransactionStatus.PENDING,
        credit_card_id=credit_card_id,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def test_projection_matches_exact_cash_flow_timeline(db, sample_user, sample_category):
    account = Account(
        user_id=sample_user.id,
        name="Conta Corrente",
        balance=Decimal("2000.00"),
        initial_balance=Decimal("2000.00"),
        is_active=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    card = CreditCard(
        user_id=sample_user.id,
        name="Nubank",
        account_id=account.id,
        credit_limit=Decimal("5000.00"),
        closing_day=3,
        due_day=10,
        is_active=True,
    )
    db.add(card)
    db.commit()
    db.refresh(card)

    _create_pending_transaction(
        db,
        sample_user.id,
        account.id,
        sample_category.id,
        amount="500.00",
        due_date=date.today() + timedelta(days=1),
        transaction_type=TransactionType.EXPENSE,
    )
    _create_pending_transaction(
        db,
        sample_user.id,
        account.id,
        sample_category.id,
        amount="1800.00",
        due_date=date.today() + timedelta(days=10),
        transaction_type=TransactionType.EXPENSE,
        credit_card_id=card.id,
    )
    _create_pending_transaction(
        db,
        sample_user.id,
        account.id,
        sample_category.id,
        amount="3000.00",
        due_date=date.today() + timedelta(days=15),
        transaction_type=TransactionType.INCOME,
    )

    projection = CashFlowProjectionService(db).get_projected_daily_balance(
        sample_user.id,
        months_ahead=1,
    )

    by_day = {
        (date.fromisoformat(item["date"]) - date.today()).days: item["projected_balance"]
        for item in projection
    }

    assert by_day[0] == "2000.00"
    assert by_day[1] == "1500.00"
    assert by_day[10] == "-300.00"
    assert by_day[15] == "2700.00"


def test_projection_is_read_only(db, sample_user, sample_account, sample_category):
    initial_count = db.query(Transaction).count()

    CashFlowProjectionService(db).get_projected_daily_balance(
        sample_user.id,
        months_ahead=1,
    )

    assert db.query(Transaction).count() == initial_count


def test_projection_includes_unmaterialized_recurring_bills(
    db, sample_user, sample_account, sample_category
):
    due = date.today() + timedelta(days=20)
    scheduled_bill = ScheduledBill(
        user_id=sample_user.id,
        name="Aluguel",
        amount=Decimal("1200.00"),
        bill_type=BillType.PAYABLE,
        due_date=due,
        account_id=sample_account.id,
        category_id=sample_category.id,
        recurrence=BillRecurrence.MONTHLY,
        status=BillStatus.PENDING,
        is_deleted=False,
        is_paused=False,
    )
    db.add(scheduled_bill)
    db.commit()
    db.refresh(scheduled_bill)

    projection = CashFlowProjectionService(db).get_projected_daily_balance(
        sample_user.id,
        months_ahead=1,
    )

    by_date = {item["date"]: item["projected_balance"] for item in projection}
    due_key = due.isoformat()
    initial_key = date.today().isoformat()

    assert due_key in by_date
    assert initial_key in by_date

    initial_balance = Decimal(by_date[initial_key])
    due_balance = Decimal(by_date[due_key])
    assert due_balance - initial_balance == Decimal("-1200.00")


def test_card_invoice_reduces_projection_exactly_on_due_day(db, sample_user, sample_category):
    """Fatura de R$ 1.000 vencendo em 15 dias reduz o saldo só no 15º dia."""
    account = Account(
        user_id=sample_user.id,
        name="Conta Corrente",
        balance=Decimal("5000.00"),
        initial_balance=Decimal("5000.00"),
        is_active=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    card = CreditCard(
        user_id=sample_user.id,
        name="Cartao Teste",
        account_id=account.id,
        credit_limit=Decimal("5000.00"),
        closing_day=3,
        due_day=18,
        is_active=True,
    )
    db.add(card)
    db.commit()
    db.refresh(card)

    # Compra no cartão: NÃO deve afetar o caixa na data da compra.
    purchase_transaction = _create_pending_transaction(
        db,
        sample_user.id,
        account.id,
        sample_category.id,
        amount="1000.00",
        due_date=date.today() + timedelta(days=15),
        transaction_type=TransactionType.EXPENSE,
        credit_card_id=card.id,
    )
    purchase_transaction.purchase_date = date.today()

    projection = CashFlowProjectionService(db).get_projected_daily_balance(
        sample_user.id,
        months_ahead=1,
    )

    by_day = {
        (date.fromisoformat(item["date"]) - date.today()).days: Decimal(item["projected_balance"])
        for item in projection
    }

    # Dia 0 até dia 14: saldo intacto (compra no cartão não mexe no caixa).
    assert by_day[0] == Decimal("5000.00")
    assert by_day[14] == Decimal("5000.00")

    # Dia 15: a fatura cai, gerando exatamente -1.000.
    assert by_day[15] == Decimal("4000.00")
    assert by_day[16] == Decimal("4000.00")


def test_paid_transactions_do_not_affect_projection(db, sample_user, sample_category):
    """Transações já liquidadas já compõem o current_balance e não são projetadas.

    Despesa de R$ 900liquidada anteontem: o saldo atual é R$ 100
    (1000 inicial - 900 pago) e a projeção fica plana em R$ 100.
    Se o filtro de pendências falhasse, a despesa cairia de novo no dia 5.
    """
    account = Account(
        user_id=sample_user.id,
        name="Conta Corrente",
        balance=Decimal("100.00"),
        initial_balance=Decimal("1000.00"),
        is_active=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    paid = _create_pending_transaction(
        db,
        sample_user.id,
        account.id,
        sample_category.id,
        amount="900.00",
        due_date=date.today() + timedelta(days=5),
        transaction_type=TransactionType.EXPENSE,
    )
    paid.status = TransactionStatus.PAID
    paid.paid_date = date.today() - timedelta(days=1)
    db.commit()

    projection = CashFlowProjectionService(db).get_projected_daily_balance(
        sample_user.id,
        months_ahead=1,
    )

    balances = [Decimal(item["projected_balance"]) for item in projection]
    assert balances
    assert all(value == Decimal("100.00") for value in balances)


def test_horizon_limits_number_of_projected_days(db, sample_user):
    projection_3m = CashFlowProjectionService(db).get_projected_daily_balance(
        sample_user.id,
        months_ahead=3,
    )
    projection_6m = CashFlowProjectionService(db).get_projected_daily_balance(
        sample_user.id,
        months_ahead=6,
    )

    assert 89 <= len(projection_3m) <= 93
    assert 181 <= len(projection_6m) <= 185
    assert len(projection_6m) > len(projection_3m)


def test_projection_accepts_only_valid_horizon(db, sample_user):
    service = CashFlowProjectionService(db)

    try:
        service.get_projected_daily_balance(sample_user.id, months_ahead=0)
        raise AssertionError("deveria falhar")
    except ValueError:
        pass

    try:
        service.get_projected_daily_balance(sample_user.id, months_ahead=25)
        raise AssertionError("deveria falhar")
    except ValueError:
        pass
