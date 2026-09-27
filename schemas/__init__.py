"""
Schemas Pydantic para validação e serialização de dados.
"""

from schemas.account_schema import (
    AccountCreate,
    AccountResponse,
    AccountUpdate,
)
from schemas.category_schema import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
)
from schemas.common import (
    ErrorResponse,
    PaginatedResponse,
    SuccessResponse,
    TokenResponse,
)
from schemas.transaction_schema import (
    TransactionCreate,
    TransactionFilter,
    TransactionResponse,
    TransactionUpdate,
)
from schemas.user_schema import (
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)

__all__ = [
    # User
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "UserUpdate",
    # Transaction
    "TransactionCreate",
    "TransactionUpdate",
    "TransactionResponse",
    "TransactionFilter",
    # Category
    "CategoryCreate",
    "CategoryResponse",
    "CategoryUpdate",
    # Account
    "AccountCreate",
    "AccountResponse",
    "AccountUpdate",
    # Common
    "PaginatedResponse",
    "ErrorResponse",
    "SuccessResponse",
    "TokenResponse",
]
