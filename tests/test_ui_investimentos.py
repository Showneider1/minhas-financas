"""Testes unitários dos callbacks da página de Investimentos.

Testa diretamente as funções Python decoradas por Dash, sem browser/Selenium,
focando nos retornos de UI (dbc.Alert) e nas exceções de negócio P0/P1.
"""

from contextlib import contextmanager
from datetime import date

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


def _patch_market_service(monkeypatch, result):
    class _FakeMarketDataService:
        last_tickers = []

        def __init__(self, db):
            self.db = db

        def update_prices_for_tickers(self, tickers):
            _FakeMarketDataService.last_tickers = tickers
            return result

    monkeypatch.setattr(invest_callbacks, "MarketDataService", _FakeMarketDataService)
    return _FakeMarketDataService


def _create_position(db, sample_user, sample_account):
    asset = InvestmentService(db).register_asset(
        user_id=sample_user.id,
        ticker="PETR4",
        name="Petrobras",
        asset_type=AssetType.STOCK,
    )
    InvestmentService(db).buy(
        asset_id=asset.id,
        user_id=sample_user.id,
        quantity=1,
        price_per_unit=1,
        account_id=sample_account.id,
        operation_date=date.today(),
        fees=0,
    )
    return asset


def test_update_market_prices_without_clicks_returns_no_update(db, monkeypatch):
    result = invest_callbacks.update_market_prices(None, {"token": "teste"})

    assert result is no_update


def test_update_market_prices_invalid_auth_returns_warning_alert(db, monkeypatch):
    result = invest_callbacks.update_market_prices(1, {})

    assert isinstance(result, dbc.Alert)
    assert result.color == "warning"
    assert "Sessão" in result.children


def test_update_market_prices_without_positions_returns_info_alert(db, monkeypatch, sample_user):
    _patch_runtime(monkeypatch, db, user_id=sample_user.id)

    result = invest_callbacks.update_market_prices(1, {"token": "teste"})

    assert isinstance(result, dbc.Alert)
    assert result.color == "info"
    assert "Nenhuma posição" in result.children


def test_update_market_prices_success_returns_success_alert(
    db, monkeypatch, sample_user, sample_account
):
    _patch_runtime(monkeypatch, db, user_id=sample_user.id)
    _create_position(db, sample_user, sample_account)
    fake_service = _patch_market_service(
        monkeypatch,
        {"updated": ["PETR4"], "failed": {}, "skipped": []},
    )

    result = invest_callbacks.update_market_prices(1, {"token": "teste"})

    assert fake_service.last_tickers == ["PETR4"]
    assert isinstance(result, dbc.Alert)
    assert result.color == "success"
    assert "Cotações atualizadas: 1 ativos." in result.children


def test_update_market_prices_failure_returns_danger_alert(
    db, monkeypatch, sample_user, sample_account
):
    _patch_runtime(monkeypatch, db, user_id=sample_user.id)
    _create_position(db, sample_user, sample_account)
    _patch_market_service(
        monkeypatch,
        {"updated": [], "failed": {"PETR4": "erro"}, "skipped": []},
    )

    result = invest_callbacks.update_market_prices(1, {"token": "teste"})

    assert isinstance(result, dbc.Alert)
    assert result.color == "danger"
    assert "Falhas: 1." in result.children
