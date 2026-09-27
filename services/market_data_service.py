"""Serviço de cotações de mercado com cache local em banco."""

import re
from datetime import date
from decimal import Decimal

import yfinance as yf
from sqlalchemy.orm import Session

from config.logging_config import app_logger
from database.models.asset_price import AssetPrice


B3_TICKER_PATTERN = re.compile(r"^[A-Z]{4}\d{1,2}$")


class MarketDataError(ValueError):
    """Falha controlada ao consultar/provider de mercado."""


class MarketDataService:
    """Atualiza preços de ativos e grava cache local para uso do dashboard."""

    def __init__(self, db: Session, provider=None):
        self.db = db
        self.provider = provider or yf

    def normalize_symbol(self, ticker: str) -> str:
        """Aplica sufixo `.SA` para ativos da B3 mantendo o ticker original no banco."""
        normalized = ticker.strip().upper()
        if not normalized:
            raise MarketDataError("Ticker inválido")
        if "." in normalized:
            return normalized
        if B3_TICKER_PATTERN.match(normalized):
            return f"{normalized}.SA"
        return normalized

    def fetch_latest_price(self, ticker: str) -> tuple[date, Decimal, str]:
        """Consulta o preço mais recente do ticker no provider externo."""
        symbol = self.normalize_symbol(ticker)
        history = self.provider.Ticker(symbol).history(period="5d", interval="1d")
        history = history.dropna(subset=["Close"])
        if history.empty:
            raise MarketDataError(f"Nenhuma cotação encontrada para {symbol}")

        last_row = history.tail(1)
        quote_date = last_row.index[0].date()
        close_price = Decimal(str(last_row["Close"].iloc[0])).quantize(Decimal("0.00000001"))
        return quote_date, close_price, "BRL"

    def update_prices_for_tickers(
        self, tickers: list[str]
    ) -> dict[str, list[str] | dict[str, str]]:
        """Atualiza o cache local de preços sem depender de rede na leitura da UI."""
        updated: list[str] = []
        failed: dict[str, str] = {}
        skipped: list[str] = []

        valid_tickers = {ticker.strip().upper() for ticker in tickers if ticker and ticker.strip()}
        for raw_ticker in valid_tickers:
            try:
                quote_date, close_price, currency = self.fetch_latest_price(raw_ticker)
                existing = (
                    self.db.query(AssetPrice)
                    .filter(
                        AssetPrice.ticker == raw_ticker,
                        AssetPrice.date == quote_date,
                        AssetPrice.provider == "yfinance",
                    )
                    .first()
                )
                if existing:
                    existing.close_price = close_price
                    existing.currency = currency
                else:
                    self.db.add(
                        AssetPrice(
                            ticker=raw_ticker,
                            date=quote_date,
                            close_price=close_price,
                            currency=currency,
                            provider="yfinance",
                        )
                    )
                self.db.commit()
                updated.append(raw_ticker)
            except MarketDataError as exc:
                skipped.append(raw_ticker)
                app_logger.warning(f"MarketData sem cotação para {raw_ticker}: {exc}")
            except Exception as exc:  # noqa: BLE001
                self.db.rollback()
                failed[raw_ticker] = str(exc)
                app_logger.error(f"Erro ao atualizar cotação de {raw_ticker}: {exc}")

        return {"updated": sorted(updated), "failed": failed, "skipped": sorted(skipped)}
