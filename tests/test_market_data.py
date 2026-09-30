"""Testes de Market Data — cache, fallback e rentabilidade (100% offline)."""

from datetime import date
from decimal import Decimal

import pandas as pd

from database.enums import AssetType
from database.models.account import Account
from services.dashboard_service import DashboardService
from services.investment_service import InvestmentService
from services.market_data_service import _PRICE_CACHE, MarketDataService


class _FakeTicker:
    def __init__(self, close_price):
        self.close_price = close_price

    def history(self, **kwargs):
        return pd.DataFrame(
            {"Close": [float(self.close_price)]},
            index=pd.to_datetime([date.today().isoformat()]),
        )


class _FakeProvider:
    def __init__(self, close_price):
        self.close_price = close_price
        self.calls = 0

    def Ticker(self, symbol):
        self.calls += 1
        return _FakeTicker(self.close_price)


class _FailingProvider:
    def Ticker(self, symbol):
        raise RuntimeError("Sem internet")


def test_normalize_symbol_adds_b3_suffix():
    service = MarketDataService(None)

    assert service.normalize_symbol("KLBN3") == "KLBN3.SA"
    assert service.normalize_symbol("PETR4") == "PETR4.SA"
    assert service.normalize_symbol("BTC-USD") == "BTC-USD"


def test_get_current_price_uses_provider_and_ttl_cache(monkeypatch):
    _PRICE_CACHE.clear()
    provider = _FakeProvider(Decimal("15.00"))
    service = MarketDataService(None, provider=provider)

    first = service.get_current_price("KLBN3")
    second = service.get_current_price("KLBN3")

    assert first == Decimal("15.00")
    assert second == Decimal("15.00")
    assert provider.calls == 1  # cache impede segunda chamada externa


def test_get_current_price_falls_back_to_average_price(monkeypatch):
    _PRICE_CACHE.clear()
    service = MarketDataService(None, provider=_FailingProvider())

    price = service.get_current_price("PETR4", fallback_price=Decimal("12.34"))

    assert price == Decimal("12.34")


def test_dashboard_net_worth_uses_market_value_not_cost(db, sample_user, monkeypatch):
    # Garante que nenhum teste acesse a internet.
    monkeypatch.setattr(
        MarketDataService,
        "get_current_price",
        lambda self, ticker, fallback_price=None: Decimal(str(fallback_price)),
    )
    account = Account(
        user_id=sample_user.id,
        name="Corretora",
        balance=Decimal("15000.00"),
        initial_balance=Decimal("15000.00"),
        is_active=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    service = InvestmentService(db)
    asset = service.register_asset(
        user_id=sample_user.id,
        ticker="KLBN3",
        name="Klabin",
        asset_type=AssetType.STOCK,
    )
    service.buy(
        asset_id=asset.id,
        user_id=sample_user.id,
        quantity="1000",
        price_per_unit="10.00",
        account_id=account.id,
        operation_date=date.today(),
        fees="0",
    )

    class _Market12:
        def get_current_price(self, ticker, fallback_price=None):
            return Decimal("12.00")

    summary = DashboardService(db).get_executive_summary(
        sample_user.id,
        month=date.today().month,
        year=date.today().year,
    )
    # Sem cotação externa: fallback é o PM (10,00).
    assert summary["investments_market_value"] == Decimal("10000.00")
    assert summary["total_invested"] == Decimal("10000.00")
    assert summary["net_worth"] == Decimal("15000.00")

    portfolio = InvestmentService(db).get_position_summary(
        sample_user.id,
        market_data_service=_Market12(),
    )
    assert portfolio["total_current_value"] == Decimal("12000.00")
    assert portfolio["total_cost"] == Decimal("10000.00")
    assert portfolio["positions"][0]["current_market_value"] == Decimal("12000.00")
    assert portfolio["positions"][0]["profitability_pct"] == 20.0

    executive = DashboardService(db).get_executive_summary(
        sample_user.id,
        month=date.today().month,
        year=date.today().year,
        market_data_service=_Market12(),
    )
    assert executive["total_invested"] == Decimal("10000.00")
    assert executive["investments_market_value"] == Decimal("12000.00")
    assert executive["market_gain"] == Decimal("2000.00")
    assert executive["net_worth"] == Decimal("17000.00")
