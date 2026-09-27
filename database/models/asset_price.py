"""Modelo de cache/histórico de preços de mercado de ativos."""

from datetime import date, datetime, timezone

from sqlalchemy import Column, Date, DateTime, Index, Integer, Numeric, String
from sqlalchemy import UniqueConstraint

from database.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AssetPrice(Base):
    """Últimos preços de mercado por ticker e data."""

    __tablename__ = "asset_prices"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(30), nullable=False)
    date = Column(Date, nullable=False)
    close_price = Column(Numeric(18, 8), nullable=False)
    currency = Column(String(3), nullable=False, default="BRL")
    provider = Column(String(50), nullable=False, default="yfinance")
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "ticker",
            "date",
            "provider",
            name="uq_asset_prices_ticker_date_provider",
        ),
        Index("ix_asset_prices_ticker_date", "ticker", "date"),
    )

    def __repr__(self) -> str:
        return f"<AssetPrice ticker={self.ticker} date={self.date} price={self.close_price}>"
