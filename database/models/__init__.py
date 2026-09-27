"""
Exporta todos os models para registro no SQLAlchemy.
"""

from database.models.account import Account, AccountType
from database.models.budget import Budget
from database.models.category import Category, TransactionType
from database.models.goal import Goal, GoalCategory, GoalStatus

# Importando o novo módulo de investimentos
from database.models.investment import Asset, AssetType, InvestmentOperation, OperationType
from database.models.password_reset_token import PasswordResetToken
from database.models.rate_limit import RateLimitHit
from database.models.refresh_token import RefreshToken
from database.models.scheduled_bill import BillRecurrence, BillStatus, BillType, ScheduledBill
from database.models.transaction import Transaction, TransactionStatus
from database.models.user import User

__all__ = [
    "User",
    "Account",
    "AccountType",
    "Category",
    "TransactionType",
    "Transaction",
    "TransactionStatus",
    "Budget",
    "Asset",
    "InvestmentOperation",
    "AssetType",
    "OperationType",
    "Goal",
    "GoalStatus",
    "GoalCategory",
    "ScheduledBill",
    "BillType",
    "BillStatus",
    "BillRecurrence",
    "PasswordResetToken",
    "RateLimitHit",
    "RefreshToken",
]
