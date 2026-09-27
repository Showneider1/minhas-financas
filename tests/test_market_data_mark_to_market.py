"""Testes do cache de preços e Mark-to-Market dentro do patrimônio."""

from datetime import date, timedelta
from decimal import Decimal

import pandas as pd

import services.market_data_service as market_data_module
from database.enums import AssetType
from database.models.account import Account
from database.models.asset_price import AssetPrice
from services.dashboard_service import DashboardService
from services.investment_service import InvestmentService
from services.market_data_service import MarketDataService


class _FakeTicker:
    def __init__(self, close_price=Decimal("15.00"), empty=False):
        self.close_price = close_price
        self.empty = empty

    def history(self, **kwargs):
        if self.empty:
            return pd.DataFrame({"Close": []}, index=pd.to_datetime([]))
        return pd.DataFrame(
            {"Close": [float(self.close_price)]},
            index=pd.to_datetime([date.today().isoformat()]),
        )


symbol_calls = []


def _patch_yfinance_calls(monkeypatch, close_price="15.00"):
    symbol_calls.clear()

    def fake_ticker(symbol):
        symbol_calls.append(symbol)
        return _FakeTicker(close_price=close_price)

    monkeypatch.setattr(market_data_module.yf, "Ticker", fake_ticker)


def test_market_data_service_persists_latest_price_with_b3_suffix(monkeypatch, db):
    _patch_yfinance_calls(monkeypatch, close_price="15.00")
    service = MarketDataService(db)

    result = service.update_prices_for_tickers(["KLBN3"])

    assert result["updated"] == ["KLBN3"]
    assert symbol_calls == ["KLBN3.SA"]

    persisted = db.query(AssetPrice).filter(AssetPrice.ticker == "KLBN3").one()
    assert persisted.close_price == Decimal("15.00000000")
    assert persisted.date == date.today()


def test_market_data_service_skips_empty_history_gracefully(monkeypatch, db):
    monkeypatch.setattr(
        market_data_module.yf,
        "Ticker",
        lambda symbol: _FakeTicker(empty=True),
    )
    service = MarketDataService(db)

    result = service.update_prices_for_tickers(["INVALID1"])

    assert result["skipped"] == ["INVALID1"]
    assert result["updated"] == []
    assert db.query(AssetPrice).filter(AssetPrice.ticker == "INVALID1").count() == 0


def test_dashboard_uses_cached_market_price_instead_of_operation_price(db, sample_user):
    account = Account(
        user_id=sample_user.id,
        name="Corretora",
        balance=Decimal("2000.00"),
        initial_balance=Decimal("2000.00"),
        is_active=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    asset = InvestmentService(db).register_asset(
        user_id=sample_user.id,
        ticker="PETR4",
        name="Petrobras",
        asset_type=AssetType.STOCK,
    )
    InvestmentService(db).buy(
        asset_id=asset.id,
        user_id=sample_user.id,
        quantity="100",
        price_per_unit="10",
        account_id=account.id,
        operation_date=date.today() - timedelta(days=2),
        fees="0",
    )

    db.add(
        AssetPrice(
            ticker="PETR4",
            date=date.today(),
            close_price=Decimal("15.00"),
            currency="BRL",
            provider="yfinance",
        )
    )
    db.commit()

    summary = DashboardService(db).get_wealth_summary(sample_user.id)

    assert summary["cash_balance"] == Decimal("1000.00")
    assert summary["investments_total"] == Decimal("1500.00")
    assert summary["net_worth"] == Decimal("2500.00")
