"""Testes de UI do módulo de Cartões de Crédito."""

from contextlib import contextmanager
from datetime import date
from decimal import Decimal

import dash_bootstrap_components as dbc
from dash import no_update

import callbacks.cartoes_callbacks as cartoes_callbacks
import callbacks.transactions_callbacks as transactions_callbacks
from database.enums import TransactionStatus, TransactionType
from database.models.account import Account
from database.models.transaction import Transaction
from services.balance_service import BalanceService
from services.credit_card_service import CreditCardService


def _patch_runtime(monkeypatch, db, user_id):
    monkeypatch.setattr(cartoes_callbacks, "resolve_user", lambda *a, **kw: user_id)

    @contextmanager
    def session_ctx():
        yield db

    monkeypatch.setattr(cartoes_callbacks, "get_db_session", session_ctx)


def _patch_transaction_runtime(monkeypatch, db, user_id):
    monkeypatch.setattr(transactions_callbacks, "resolve_user", lambda *a, **kw: user_id)

    @contextmanager
    def session_ctx():
        yield db

    monkeypatch.setattr(transactions_callbacks, "get_db_session", session_ctx)


def _call_create_credit_card(monkeypatch, db, user_id, **overrides):
    _patch_runtime(monkeypatch, db, user_id)
    args = {
        "n_clicks": 1,
        "name": "Nubank",
        "limit": "5000",
        "closing_day": 3,
        "due_day": 10,
        "auth_data": {"token": "teste"},
        "reload_counter": 0,
    }
    args.update(overrides)
    return cartoes_callbacks.create_credit_card(**args)


def test_create_credit_card_callback_success(db, monkeypatch, sample_user):
    result = _call_create_credit_card(monkeypatch, db, sample_user.id)

    feedback, toast, toast_open, reload, modal_open = result
    assert feedback == ""
    assert isinstance(toast, dbc.Alert)
    assert toast.color == "success"
    assert "Nubank" in toast.children
    assert toast_open is True
    assert reload == 1
    assert modal_open is False

    cards = CreditCardService(db).__class__.__mro__  # noqa: F841
    from database.models.credit_card import CreditCard

    card = db.query(CreditCard).filter(CreditCard.user_id == sample_user.id).one()
    assert card.name == "Nubank"
    assert card.credit_limit == Decimal("5000.00")
    assert card.closing_day == 3
    assert card.due_day == 10


def test_create_credit_card_callback_rejects_invalid_closing_day(db, monkeypatch, sample_user):
    result = _call_create_credit_card(
        monkeypatch,
        db,
        sample_user.id,
        closing_day=32,
    )

    feedback, toast, toast_open, reload, modal_open = result
    assert isinstance(feedback, dbc.Alert)
    assert feedback.color == "warning"
    assert "Dia de fechamento deve estar entre 1 e 31." in feedback.children
    assert toast is not None
    assert toast_open is not None
    assert reload is not None
    assert modal_open is True

    from database.models.credit_card import CreditCard

    assert db.query(CreditCard).filter(CreditCard.user_id == sample_user.id).count() == 0


def test_transaction_modal_submits_credit_card_purchase(
    db, monkeypatch, sample_user, sample_category
):
    card = CreditCardService(db).create_credit_card(
        user_id=sample_user.id,
        name="Nubank",
        credit_limit=Decimal("5000.00"),
        closing_day=3,
        due_day=10,
    )

    service_calls = []

    class FakeCreditCardService:
        def __init__(self, db_session):
            self.db = db_session

        def register_purchase(self, **kwargs):
            service_calls.append(kwargs)
            return []

    monkeypatch.setattr(
        transactions_callbacks,
        "CreditCardService",
        FakeCreditCardService,
    )
    _patch_transaction_runtime(monkeypatch, db, sample_user.id)

    result = transactions_callbacks.salvar_transacao(
        1,
        {"token": "teste"},
        None,
        "EXPENSE",
        "CARTAO",
        "1200,00",
        "Notebook",
        str(sample_category.id),
        None,
        str(card.id),
        None,
        None,
        date(2026, 10, 1).isoformat(),
        None,
        None,
        True,
        1,
        1,
        3,
        0,
    )

    alert, reload, modal_open = result
    assert isinstance(alert, dbc.Alert)
    assert alert.color == "success"
    assert "Compra no cartão registrada com sucesso!" in alert.children
    assert reload == 1
    assert modal_open is False

    assert len(service_calls) == 1
    call = service_calls[0]
    assert call["user_id"] == sample_user.id
    assert call["credit_card_id"] == card.id
    assert call["amount"] == Decimal("1200.00")
    assert call["purchase_date"] == date(2026, 10, 1)
    assert call["installments"] == 3


def test_transaction_modal_credit_card_purchase_persists_installments(
    db, monkeypatch, sample_user, sample_category
):
    card = CreditCardService(db).create_credit_card(
        user_id=sample_user.id,
        name="Nubank",
        credit_limit=Decimal("5000.00"),
        closing_day=3,
        due_day=10,
    )
    _patch_transaction_runtime(monkeypatch, db, sample_user.id)

    result = transactions_callbacks.salvar_transacao(
        1,
        {"token": "teste"},
        None,
        "EXPENSE",
        "CARTAO",
        "1200,00",
        "Notebook",
        str(sample_category.id),
        None,
        str(card.id),
        None,
        None,
        date(2026, 10, 1).isoformat(),
        None,
        None,
        True,
        1,
        1,
        3,
        0,
    )

    alert, _reload, modal_open = result
    assert alert.color == "success"
    assert modal_open is False

    transactions = (
        db.query(Transaction)
        .filter(Transaction.credit_card_id == card.id)
        .order_by(Transaction.installment_number.asc())
        .all()
    )
    assert len(transactions) == 3
    assert [t.base_amount for t in transactions] == [
        Decimal("400.00"),
        Decimal("400.00"),
        Decimal("400.00"),
    ]
    assert [t.installment_number for t in transactions] == [1, 2, 3]
    assert all(t.total_installments == 3 for t in transactions)
    assert all(t.paid_date is None for t in transactions)


def _call_pagar_fatura(monkeypatch, db, user_id, **overrides):
    _patch_runtime(monkeypatch, db, user_id)
    args = {
        "n_clicks": 1,
        "card_id": 0,
        "month": 1,
        "year": 2026,
        "source_account_id": 0,
        "auth_data": {"token": "teste"},
        "cartoes_reload": 0,
        "dashboard_reload": 0,
    }
    args.update(overrides)
    return cartoes_callbacks.pagar_fatura(**args)


def _seed_invoice(db, sample_user, sample_category, *, amount=Decimal("300.00"), limit=Decimal("5000.00")):
    service = CreditCardService(db)
    card = service.create_credit_card(
        user_id=sample_user.id,
        name="Nubank",
        credit_limit=limit,
        closing_day=3,
        due_day=10,
    )
    purchase = service.register_purchase(
        user_id=sample_user.id,
        credit_card_id=card.id,
        amount=amount,
        purchase_date=date(2026, 10, 5),
        description="Supermercado",
        category_id=sample_category.id,
    )[0]
    db.refresh(purchase)
    return card, purchase


def test_pay_invoice_button_pays_and_moves_funds(
    db, monkeypatch, sample_user, sample_account, sample_category
):
    """Botão Pagar Fatura: paga a fatura, debita a conta origem e registra a transferência."""
    card, purchase = _seed_invoice(db, sample_user, sample_category)

    result = _call_pagar_fatura(
        monkeypatch,
        db,
        sample_user.id,
        card_id=card.id,
        month=purchase.due_date.month,
        year=purchase.due_date.year,
        source_account_id=sample_account.id,
    )

    feedback, cartoes_reload, dashboard_reload = result
    assert isinstance(feedback, dbc.Alert)
    assert feedback.color == "success"
    assert "Fatura paga com sucesso!" in feedback.children
    assert cartoes_reload == 1
    assert dashboard_reload == 1

    db.refresh(purchase)
    assert purchase.status == TransactionStatus.PAID
    assert purchase.paid_date is not None

    db.refresh(sample_account)
    assert sample_account.balance == Decimal("4700.00")

    anchor = db.get(Account, card.account_id)
    db.refresh(anchor)
    assert anchor.balance == Decimal("0.00")

    computed_source = BalanceService(db).get_account_balance(
        sample_account.id, sample_user.id
    )
    assert computed_source == Decimal("4700.00")

    computed_anchor = BalanceService(db).get_account_balance(
        card.account_id, sample_user.id
    )
    assert computed_anchor == Decimal("0.00")

    payment = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == sample_user.id,
            Transaction.transaction_type == TransactionType.TRANSFER,
            Transaction.account_id == sample_account.id,
        )
        .one()
    )
    assert payment.base_amount == Decimal("300.00")
    assert payment.destination_account_id == card.account_id
    assert payment.status == TransactionStatus.PAID
    assert payment.paid_date is not None


def test_pay_invoice_button_without_clicks_returns_no_update(db, monkeypatch, sample_user):
    """P0 Blindagem: sem clique real (n_clicks None) o callback não pode executar nada."""
    result = _call_pagar_fatura(monkeypatch, db, sample_user.id, n_clicks=None)

    assert result == (no_update, no_update, no_update)


def test_pay_invoice_button_insufficient_balance_keeps_invoice_pending(
    db, monkeypatch, sample_user, sample_account, sample_category
):
    """Saldo insuficiente na conta origem: fatura permanece pendente e saldo intacto."""
    card, purchase = _seed_invoice(
        db,
        sample_user,
        sample_category,
        amount=Decimal("5500.00"),
        limit=Decimal("10000.00"),
    )

    result = _call_pagar_fatura(
        monkeypatch,
        db,
        sample_user.id,
        card_id=card.id,
        month=purchase.due_date.month,
        year=purchase.due_date.year,
        source_account_id=sample_account.id,
    )

    feedback, cartoes_reload, dashboard_reload = result
    assert isinstance(feedback, dbc.Alert)
    assert feedback.color == "warning"
    assert "Saldo insuficiente" in feedback.children
    assert cartoes_reload is no_update
    assert dashboard_reload is no_update

    db.refresh(purchase)
    assert purchase.status == TransactionStatus.PENDING
    assert purchase.paid_date is None

    db.refresh(sample_account)
    assert sample_account.balance == Decimal("5000.00")
