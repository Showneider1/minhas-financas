"""Enums canônicos do domínio financeiro — ÚNICA fonte de verdade (P1).

Regras:
- Todos `str, enum.Enum`: serializam em JSON, aceitos crus no Pydantic e
  armazenados como VARCHAR pelo SQLAlchemy (`native_enum=False` nos models),
  compatível com SQLite hoje e PostgreSQL/Supabase amanhã.
- Valores idênticos aos legados (migração sem reescrita de dados).
- Models, schemas e services importam daqui. Nada de redefinir.
"""
import enum


class TransactionType(str, enum.Enum):
    """Tipo de lançamento."""
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"


class TransactionStatus(str, enum.Enum):
    """Status do lançamento (sincronizado com paid_date em escrita)."""
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class AccountType(str, enum.Enum):
    """Tipo de conta."""
    CHECKING = "checking"
    SAVINGS = "savings"
    INVESTMENT = "investment"
    CREDIT_CARD = "credit_card"
    CASH = "cash"
    OTHER = "other"


class GoalStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class GoalCategory(str, enum.Enum):
    EMERGENCY_FUND = "emergency_fund"
    TRAVEL = "travel"
    EDUCATION = "education"
    PROPERTY = "property"
    VEHICLE = "vehicle"
    RETIREMENT = "retirement"
    INVESTMENT = "investment"
    OTHER = "other"


class AssetType(str, enum.Enum):
    """Tipos de ativos financeiros."""
    STOCK = "STOCK"
    FII = "FII"
    FIXED_INCOME = "FIXED"
    CRYPTO = "CRYPTO"
    CURRENCY = "CURRENCY"
    ETF = "ETF"


class OperationType(str, enum.Enum):
    """Tipos de operação de investimento."""
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    INTEREST = "INTEREST"
    SPLIT = "SPLIT"


class BillType(str, enum.Enum):
    PAYABLE = "payable"
    RECEIVABLE = "receivable"


class BillStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class BillRecurrence(str, enum.Enum):
    NONE = "none"
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    YEARLY = "yearly"
    QUARTERLY = "quarterly"
