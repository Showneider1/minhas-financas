"""
Exporta todos os models para registro no SQLAlchemy.
"""
from database.models.user import User
from database.models.account import Account, AccountType
from database.models.category import Category, TransactionType
from database.models.transaction import Transaction, TransactionStatus
from database.models.budget import Budget
# Importando o novo módulo de investimentos
from database.models.investment import Asset, InvestmentOperation, AssetType, OperationType

__all__ = [
    "User",
    "Account", "AccountType",
    "Category", "TransactionType",
    "Transaction", "TransactionStatus",
    "Budget",
    "Asset", "InvestmentOperation", "AssetType", "OperationType",
]