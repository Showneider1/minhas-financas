"""
Modelo de Investimentos (Ativos e Operações).
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database.base import Base
from database.enums import AssetType, OperationType  # canônicos (P1)

__all__ = ["Asset", "InvestmentOperation", "AssetType", "OperationType"]


def _utcnow():
    """
    Retorna datetime atual em UTC timezone-aware.
    FIX: substitui datetime.utcnow() depreciado no Python 3.12+ / removido no 3.13.
    Mantém padrão já adotado em user.py e transaction.py.
    """
    return datetime.now(timezone.utc)


class Asset(Base):
    """
    Cadastro do Ativo (O 'Papel').
    """

    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), nullable=False, index=True)  # Código (PETR4, BTC)
    name = Column(String(100), nullable=False)  # Nome (Petrobras PN)
    asset_type = Column(Enum(AssetType, native_enum=False), nullable=False)
    sector = Column(String(50), nullable=True)  # Setor (Bancos, Energia...)

    # Meta de alocação da estratégia (Buy & Hold), em % do patrimônio.
    # Decimal(5,2): 0,00–100,00. A soma dos alvos do usuário é validada
    # em código (<= 100) por InvestmentService.set_target_allocation —
    # CHECK no banco não é possível (agrega outra tabela).
    target_allocation_pct = Column(Numeric(5, 2), nullable=False, default=0, server_default="0")

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Relacionamentos
    user = relationship("User", back_populates="assets")
    operations = relationship(
        "InvestmentOperation", back_populates="asset", cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("ticker", "user_id", name="uq_asset_ticker_user"),)


class InvestmentOperation(Base):
    """
    Histórico de movimentações (Carteira).
    """

    __tablename__ = "investment_operations"

    id = Column(Integer, primary_key=True, index=True)

    # Vínculos
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(
        Integer, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True
    )  # De qual conta saiu o dinheiro?

    # Liquidação no caixa (P1 liquidação): 1:1 com a Transaction de despesa/
    # receita correspondente. NULL apenas para SPLIT (sem liquidação).
    transaction_id = Column(
        Integer,
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )

    # Dados da Operação
    operation_type = Column(Enum(OperationType, native_enum=False), nullable=False)
    date = Column(Date, nullable=False, index=True)

    # Quantidades/preços (Numeric 18,8 — cotas fracionárias cripto/fundos;
    # nunca Float; ADR-002 + P1 investimentos).
    quantity = Column(Numeric(18, 8), nullable=False)  # Quantidade
    price_per_unit = Column(Numeric(18, 8), nullable=False)  # Preço na data
    fees = Column(Numeric(18, 8), default=0)  # Taxas (B3, Corretagem)
    total_amount = Column(Numeric(18, 8), nullable=False)  # BUY: qtd*preço+taxas

    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)  # FIX: timezone-aware

    # Relacionamentos
    asset = relationship("Asset", back_populates="operations")
    account = relationship("Account")
    transaction = relationship("Transaction")

    __table_args__ = (Index("ix_investment_ops_asset_date", "asset_id", "date"),)
