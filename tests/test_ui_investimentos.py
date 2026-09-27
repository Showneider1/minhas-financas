"""Testes unitários dos callbacks da página de Investimentos.

Testa diretamente as funções Python decoradas por Dash, sem browser/Selenium,
focando nos retornos de UI (dbc.Alert) e nas exceções de negócio P0/P1.
"""

from contextlib import contextmanager

import dash_bootstrap_components as dbc
from dash import no_update

import callbacks.investimentos_callbacks as invest_callbacks
from database.enums import AssetType
from services.investment_service import InvestmentService


def _call_save(**overrides):
    defaults = {
        "n_clicks": 1,
        "auth_data": {"token": "teste"},
        "edit_id": None,
        "op_type": "BUY",
        "asset_id": None,
        "account_id": None,
        "qty": None,
        "price": None,
        "fees": None,
        "op_date": None,
        "notes": None,
    }
    defaults.update(overrides)
    return invest_callbacks.save_investment_operation(**defaults)


def _patch_runtime(monkeypatch, db, user_id=None):
    """Substitui dependências por stubs determinísticos nos testes unitários."""
    monkeypatch.setattr(invest_callbacks, "hit", lambda *args, **kwargs: (True, None))
    monkeypatch.setattr(invest_callbacks, "client_ip", lambda: "127.0.0.1")

    @contextmanager
    def session_ctx():
        yield db

    monkeypatch.setattr(invest_callbacks, "get_db_session", session_ctx)
    if user_id is not None:
        monkeypatch.setattr(invest_callbacks, "resolve_user", lambda *args, **kwargs: user_id)


def test_save_investment_without_clicks_does_not_call_service(db, monkeypatch):
    _patch_runtime(monkeypatch, db, user_id=1)

    result = _call_save(n_clicks=None)

    assert result == (no_update, no_update, no_update, no_update)


def test_save_investment_invalid_auth_returns_warning_alert(db, monkeypatch):
    _patch_runtime(monkeypatch, db)

    result = _call_save(auth_data={})

    modal_alert = result[0]
    assert isinstance(modal_alert, dbc.Alert)
    assert modal_alert.color == "warning"
    assert "Sessão" in modal_alert.children
    assert result[1] is True


def test_save_buy_without_balance_returns_danger_alert(
    db, monkeypatch, sample_user, sample_account
):
    _patch_runtime(monkeypatch, db, user_id=sample_user.id)
    asset = InvestmentService(db).register_asset(
        user_id=sample_user.id,
        ticker="PETR4",
        name="Petrobras",
        asset_type=AssetType.STOCK,
    )

    result = _call_save(
        asset_id=str(asset.id),
        account_id=str(sample_account.id),
        qty=100,
        price=100,
        fees=0,
        op_date="2027-01-10",
    )

    modal_alert = result[0]
    assert isinstance(modal_alert, dbc.Alert)
    assert modal_alert.color == "danger"
    assert "Saldo insuficiente" in modal_alert.children
    assert result[1] is True


def test_save_buy_success_returns_success_alert(db, monkeypatch, sample_user, sample_account):
    _patch_runtime(monkeypatch, db, user_id=sample_user.id)
    asset = InvestmentService(db).register_asset(
        user_id=sample_user.id,
        ticker="PETR4",
        name="Petrobras",
        asset_type=AssetType.STOCK,
    )

    result = _call_save(
        asset_id=str(asset.id),
        account_id=str(sample_account.id),
        qty=1,
        price=100,
        fees=0,
        op_date="2027-01-10",
        notes="compra teste",
    )

    assert result[0] == ""
    assert result[1] is False
    success_alert = result[2]
    assert isinstance(success_alert, dbc.Alert)
    assert success_alert.color == "success"
    assert "Compra registrada com sucesso." in success_alert.children
    assert result[3] is True
