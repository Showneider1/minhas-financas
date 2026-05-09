"""
Modelo de Investimentos (Ativos e Operações).
"""
from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database.base import Base
import enum


def _utcnow():
    """
    Retorna datetime atual em UTC timezone-aware.
    FIX: substitui datetime.utcnow() depreciado no Python 3.12+ / removido no 3.13.
    Mantém padrão já adotado em user.py e transaction.py.
    """
    return datetime.now(timezone.utc)


class AssetType(enum.Enum):
    """Tipos de Ativos Financeiros"""
    STOCK        = "STOCK"    # Ações (ex: PETR4)
    FII          = "FII"      # Fundos Imobiliários (ex: MXRF11)
    FIXED_INCOME = "FIXED"    # Renda Fixa (ex: Tesouro Selic)
    CRYPTO       = "CRYPTO"   # Criptomoedas (ex: BTC)
    CURRENCY     = "CURRENCY" # Moedas (ex: USD)
    ETF          = "ETF"      # ETFs (ex: IVVB11)


class OperationType(enum.Enum):
    """Tipos de Operação"""
    BUY      = "BUY"      # Compra
    SELL     = "SELL"     # Venda
    DIVIDEND = "DIVIDEND" # Dividendos / Proventos
    INTEREST = "INTEREST" # Juros sobre Capital / Rendimentos
    SPLIT    = "SPLIT"    # Desdobramento


class Asset(Base):
    """
    Cadastro do Ativo (O 'Papel').
    """
    __tablename__ = "assets"

    id         = Column(Integer,          primary_key=True, index=True)
    ticker     = Column(String(20),        nullable=False, index=True)  # Código (PETR4, BTC)
    name       = Column(String(100),       nullable=False)              # Nome (Petrobras PN)
    asset_type = Column(Enum(AssetType),   nullable=False)
    sector     = Column(String(50),        nullable=True)               # Setor (Bancos, Energia...)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relacionamentos
    user       = relationship("User",                back_populates="assets")
    operations = relationship("InvestmentOperation", back_populates="asset", cascade="all, delete-orphan")


class InvestmentOperation(Base):
    """
    Histórico de movimentações (Carteira).
    """
    __tablename__ = "investment_operations"

    id = Column(Integer, primary_key=True, index=True)

    # Vínculos
    asset_id   = Column(Integer, ForeignKey("assets.id"),   nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)  # De qual conta saiu o dinheiro?

    # Dados da Operação
    operation_type = Column(Enum(OperationType), nullable=False)
    date           = Column(Date, nullable=False)

    quantity       = Column(Float, nullable=False)  # Quantidade
    price_per_unit = Column(Float, nullable=False)  # Preço na data
    fees           = Column(Float, default=0.0)     # Taxas (B3, Corretagem)
    total_amount   = Column(Float, nullable=False)  # (Qtd * Preço) + Taxas

    notes      = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)  # FIX: timezone-aware

    # Relacionamentos
    asset   = relationship("Asset",   back_populates="operations")
    account = relationship("Account")
