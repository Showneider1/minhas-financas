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


def _call_salvar(**overrides):
    hoje = date.today()
    args = {
        "n_clicks": 1,
        "auth_data": {"token": "teste"},
        "edit_id": None,
        "tipo": "EXPENSE",
        "metodo": "CONTA",
        "valor": "10,00",
        "descricao": "Supermercado",
        "categoria_id": None,
        "conta_id": None,
        "cartao_id": None,
        "conta_origem_id": None,
        "conta_destino_id": None,
        "data_compra": hoje.isoformat(),
        "data_vencimento": hoje.isoformat(),
        "data_pagamento": hoje.isoformat(),
        "pago": True,
        "parcela_atual": 1,
        "total_parcelas": 1,
        "cartao_parcelas": 1,
        "reload_counter": 0,
    }
    args.update(overrides)
    return transaction_callbacks.salvar_transacao(**args)


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
    result = transaction_callbacks.alternar_secoes_transacao("TRANSFER", "CONTA")
    standard_style, transfer_style = result[0], result[1]

    assert standard_style == {"display": "none"}
    assert transfer_style == {"display": "block"}


def test_alternar_secoes_para_despesa():
    result = transaction_callbacks.alternar_secoes_transacao("EXPENSE", "CONTA")
    standard_style, transfer_style = result[0], result[1]

    assert standard_style == {"display": "block"}
    assert transfer_style == {"display": "none"}


def test_salvar_transferencia_valida(db, monkeypatch, sample_user):
    origin, destination = _create_accounts(db, sample_user.id)
    _create_transfer_category(db, sample_user.id)
    _patch_runtime(monkeypatch, db, sample_user.id)

    resultado = _call_salvar(
        tipo="TRANSFER",
        metodo="CONTA",
        valor="150,00",
        descricao="Transferência entre contas",
        categoria_id=None,
        conta_id=None,
        cartao_id=None,
        conta_origem_id=str(origin.id),
        conta_destino_id=str(destination.id),
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

    resultado = _call_salvar(
        tipo="TRANSFER",
        metodo="CONTA",
        valor="150,00",
        descricao="Transferência inválida",
        categoria_id=None,
        conta_id=None,
        cartao_id=None,
        conta_origem_id=str(origin.id),
        conta_destino_id=str(origin.id),
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

    resultado = _call_salvar(
        tipo="TRANSFER",
        metodo="CONTA",
        valor="9999,00",
        descricao="Transferência sem saldo",
        categoria_id=None,
        conta_id=None,
        cartao_id=None,
        conta_origem_id=str(origin.id),
        conta_destino_id=str(destination.id),
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


def test_salvar_transacao_sem_conta_retorna_alerta(db, monkeypatch, sample_user, sample_category):
    _patch_runtime(monkeypatch, db, sample_user.id)

    resultado = _call_salvar(
        tipo="EXPENSE",
        metodo="CONTA",
        valor="10,00",
        descricao="Supermercado",
        categoria_id=str(sample_category.id),
        conta_id=None,
        cartao_id=None,
        conta_origem_id=None,
        conta_destino_id=None,
    )

    alerta, _reload, modal_aberto = resultado
    assert isinstance(alerta, dbc.Alert)
    assert alerta.color == "warning"
    assert "Selecione uma conta" in alerta.children
    assert modal_aberto is True


def test_salvar_transacao_com_valor_negativo_retorna_alerta(
    db, monkeypatch, sample_user, sample_category, sample_account
):
    _patch_runtime(monkeypatch, db, sample_user.id)

    resultado = _call_salvar(
        tipo="EXPENSE",
        metodo="CONTA",
        valor="-10,00",
        descricao="Supermercado",
        categoria_id=str(sample_category.id),
        conta_id=str(sample_account.id),
        cartao_id=None,
        conta_origem_id=None,
        conta_destino_id=None,
    )

    alerta, _reload, modal_aberto = resultado
    assert isinstance(alerta, dbc.Alert)
    assert alerta.color == "warning"
    assert "Valor deve ser maior que zero" in alerta.children
    assert modal_aberto is True
    assert db.query(Transaction).count() == 0
