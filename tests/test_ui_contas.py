"""Testes do cadastro de contas na UI de Configurações."""

from contextlib import contextmanager
from decimal import Decimal
from types import SimpleNamespace

import dash_bootstrap_components as dbc
from dash import no_update

import callbacks.config_callbacks as config_callbacks
from database.enums import AccountType
from database.models.account import Account


def _patch_runtime(monkeypatch, db, user_id):
    monkeypatch.setattr(config_callbacks, "resolve_user", lambda *a, **kw: user_id)

    @contextmanager
    def session_ctx():
        yield db

    monkeypatch.setattr(config_callbacks, "get_db_session", session_ctx)
    monkeypatch.setattr(
        config_callbacks,
        "ctx",
        SimpleNamespace(triggered_id="btn-save-acc"),
    )


def _call_save(monkeypatch, db, user_id, **overrides):
    _patch_runtime(monkeypatch, db, user_id)
    args = {
        "n_cat": 0,
        "n_acc": 1,
        "n_card": 0,
        "cat_name": "",
        "cat_type": "EXPENSE",
        "cat_color": "#3498db",
        "cat_parent": None,
        "acc_name": "Nubank",
        "acc_type": AccountType.CHECKING.value,
        "acc_balance": 100,
        "card_name": "",
        "card_limit": 0,
        "card_close": 1,
        "card_due": 10,
        "auth_data": {"token": "teste"},
        "trigger_val": 0,
    }
    args.update(overrides)
    return config_callbacks.save_data(**args)


def test_create_account_uses_valid_account_type_enum(db, monkeypatch, sample_user):
    result = _call_save(monkeypatch, db, sample_user.id)

    assert result[0] == 1
    assert result[3] == ""
    assert result[6] is False

    account = db.query(Account).filter(Account.user_id == sample_user.id).one()
    assert account.name == "Nubank"
    assert account.account_type == AccountType.CHECKING
    assert account.initial_balance == Decimal("100.00")
    assert account.balance == Decimal("100.00")


def test_create_account_without_name_keeps_modal_open(db, monkeypatch, sample_user):
    result = _call_save(monkeypatch, db, sample_user.id, acc_name=" ")

    assert result[0] is no_update
    assert isinstance(result[3], dbc.Alert)
    assert "Informe o nome da conta." in result[3].children
    assert result[6] is True
    assert db.query(Account).filter(Account.user_id == sample_user.id).count() == 0


def test_create_account_with_invalid_balance_keeps_modal_open(db, monkeypatch, sample_user):
    result = _call_save(monkeypatch, db, sample_user.id, acc_balance="NaN")

    assert result[0] is no_update
    assert isinstance(result[3], dbc.Alert)
    assert "Saldo inicial inválido." in result[3].children
    assert result[6] is True
    assert db.query(Account).filter(Account.user_id == sample_user.id).count() == 0
