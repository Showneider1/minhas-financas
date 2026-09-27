"""Testes do modal global de nova transação (Receita, Despesa e Transferência)."""

from contextlib import contextmanager
from datetime import date
from decimal import Decimal

import dash_bootstrap_components as dbc

import callbacks.transactions_callbacks as transaction_callbacks
from database.enums import TransactionType
from database.models.account import Account
from database.models.category import Category
from database.models.transaction import Transaction
from services.balance_service import BalanceService


def _patch_runtime(monkeypatch, db, user_id):
    monkeypatch.setattr(transaction_callbacks, "resolve_user", lambda *a, **kw: user_id)

    @contextmanager
    def session_ctx():
        yield db

    monkeypatch.setattr(transaction_callbacks, "get_db_session", session_ctx)


def _create_accounts(db, user_id):
    origin = Account(
        user_id=user_id,
        name="Conta Origem",
        balance=Decimal("1000.00"),
        initial_balance=Decimal("1000.00"),
        is_active=True,
    )
    destination = Account(
        user_id=user_id,
        name="Conta Destino",
        balance=Decimal("500.00"),
        initial_balance=Decimal("500.00"),
        is_active=True,
    )
    db.add_all([origin, destination])
    db.commit()
    db.refresh(origin)
    db.refresh(destination)
    return origin, destination


def _create_transfer_category(db, user_id):
    category = Category(
        user_id=user_id,
        name="Transferência",
        transaction_type=TransactionType.TRANSFER,
        is_system=False,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def test_alternar_secoes_para_transferencia():
    standard_style, transfer_style = transaction_callbacks.alternar_secoes_transacao("TRANSFER")

    assert standard_style == {"display": "none"}
    assert transfer_style == {"display": "block"}


def test_alternar_secoes_para_despesa():
    standard_style, transfer_style = transaction_callbacks.alternar_secoes_transacao("EXPENSE")

    assert standard_style == {"display": "block"}
    assert transfer_style == {"display": "none"}


def test_salvar_transferencia_valida(db, monkeypatch, sample_user):
    origin, destination = _create_accounts(db, sample_user.id)
    _create_transfer_category(db, sample_user.id)
    _patch_runtime(monkeypatch, db, sample_user.id)
    hoje = date.today()

    resultado = transaction_callbacks.salvar_transacao(
        1,
        {"token": "teste"},
        None,
        "TRANSFER",
        "150,00",
        "Transferência entre contas",
        None,
        str(origin.id),
        str(destination.id),
        hoje.isoformat(),
        hoje.isoformat(),
        hoje.isoformat(),
        True,
        [],
        1,
        1,
        0,
    )

    alerta, reload, modal_aberto = resultado
    assert isinstance(alerta, dbc.Alert)
    assert alerta.color == "success"
    assert "Transferência criada com sucesso" in alerta.children
    assert reload == 1
    assert modal_aberto is False

    transferencia = (
        db.query(Transaction).filter(Transaction.transaction_type == TransactionType.TRANSFER).one()
    )
    assert transferencia.account_id == origin.id
    assert transferencia.destination_account_id == destination.id
    assert transferencia.base_amount == Decimal("150.00")

    balances = BalanceService(db)
    assert balances.get_account_balance(origin.id, sample_user.id) == Decimal("850.00")
    assert balances.get_account_balance(destination.id, sample_user.id) == Decimal("650.00")


def test_salvar_transferencia_com_contas_iguais(db, monkeypatch, sample_user):
    origin, destination = _create_accounts(db, sample_user.id)
    _create_transfer_category(db, sample_user.id)
    _patch_runtime(monkeypatch, db, sample_user.id)
    hoje = date.today()

    resultado = transaction_callbacks.salvar_transacao(
        1,
        {"token": "teste"},
        None,
        "TRANSFER",
        "150,00",
        "Transferência inválida",
        None,
        str(origin.id),
        str(origin.id),
        hoje.isoformat(),
        hoje.isoformat(),
        hoje.isoformat(),
        True,
        [],
        1,
        1,
        0,
    )

    alerta, reload, modal_aberto = resultado
    assert isinstance(alerta, dbc.Alert)
    assert alerta.color == "warning"
    assert "Conta de origem e destino devem ser diferentes" in alerta.children
    assert reload is not None
    assert modal_aberto is True
    assert (
        db.query(Transaction)
        .filter(Transaction.transaction_type == TransactionType.TRANSFER)
        .count()
        == 0
    )


def test_salvar_transferencia_com_saldo_insuficiente(db, monkeypatch, sample_user):
    origin, destination = _create_accounts(db, sample_user.id)
    _create_transfer_category(db, sample_user.id)
    _patch_runtime(monkeypatch, db, sample_user.id)
    hoje = date.today()

    resultado = transaction_callbacks.salvar_transacao(
        1,
        {"token": "teste"},
        None,
        "TRANSFER",
        "9999,00",
        "Transferência sem saldo",
        None,
        str(origin.id),
        str(destination.id),
        hoje.isoformat(),
        hoje.isoformat(),
        hoje.isoformat(),
        True,
        [],
        1,
        1,
        0,
    )

    alerta, _reload, modal_aberto = resultado
    assert isinstance(alerta, dbc.Alert)
    assert alerta.color == "warning"
    assert "Saldo insuficiente" in alerta.children
    assert modal_aberto is True
    assert (
        db.query(Transaction)
        .filter(Transaction.transaction_type == TransactionType.TRANSFER)
        .count()
        == 0
    )
