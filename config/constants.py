"""
Constantes da aplicação.
"""

# ===============================
# HTTP STATUS CODES
# ===============================
HTTP_200_OK = 200
HTTP_201_CREATED = 201
HTTP_204_NO_CONTENT = 204
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404
HTTP_409_CONFLICT = 409
HTTP_422_UNPROCESSABLE_ENTITY = 422
HTTP_429_TOO_MANY_REQUESTS = 429
HTTP_500_INTERNAL_SERVER_ERROR = 500

# ===============================
# TRANSAÇÕES
# ===============================
TRANSACTION_STATUS = {
    "PENDING": "pending",
    "PAID": "paid",
    "OVERDUE": "overdue",
    "CANCELED": "canceled",
}

TRANSACTION_TYPES = {
    "INCOME": "income",
    "EXPENSE": "expense",
}

# ===============================
# CONTAS
# ===============================
ACCOUNT_TYPES = {
    "CHECKING": "checking",
    "SAVINGS": "savings",
    "INVESTMENT": "investment",
    "CREDIT_CARD": "credit_card",
    "CASH": "cash",
    "OTHER": "other",
}

# ===============================
# MENSAGENS DE ERRO
# ===============================
ERROR_MESSAGES = {
    "INVALID_CREDENTIALS": "Email ou senha inválidos",
    "USER_NOT_FOUND": "Usuário não encontrado",
    "USER_INACTIVE": "Usuário inativo",
    "EMAIL_ALREADY_EXISTS": "Email já cadastrado",
    "INVALID_TOKEN": "Token inválido ou expirado",
    "UNAUTHORIZED": "Não autorizado",
    "FORBIDDEN": "Acesso negado",
    "NOT_FOUND": "Recurso não encontrado",
    "VALIDATION_ERROR": "Erro de validação",
    "INTERNAL_ERROR": "Erro interno do servidor",
    "RATE_LIMIT_EXCEEDED": "Limite de requisições excedido",
    "INSUFFICIENT_BALANCE": "Saldo insuficiente",
    "TRANSACTION_NOT_FOUND": "Transação não encontrada",
    "ACCOUNT_NOT_FOUND": "Conta não encontrada",
    "CATEGORY_NOT_FOUND": "Categoria não encontrada",
}

# ===============================
# CACHE KEYS
# ===============================
CACHE_KEYS = {
    "USER_PROFILE": "user:profile:{user_id}",
    "USER_ACCOUNTS": "user:accounts:{user_id}",
    "ACCOUNT_BALANCE": "account:balance:{account_id}",
    "CATEGORIES": "categories:user:{user_id}",
    "DASHBOARD_DATA": "dashboard:{user_id}:{period}",
    "TRANSACTIONS_LIST": "transactions:{user_id}:{page}:{filters_hash}",
}

# ===============================
# AUDIT ACTIONS
# ===============================
AUDIT_ACTIONS = {
    "USER_LOGIN": "user.login",
    "USER_LOGOUT": "user.logout",
    "USER_REGISTER": "user.register",
    "USER_UPDATE": "user.update",
    "USER_DELETE": "user.delete",
    "TRANSACTION_CREATE": "transaction.create",
    "TRANSACTION_UPDATE": "transaction.update",
    "TRANSACTION_DELETE": "transaction.delete",
    "ACCOUNT_CREATE": "account.create",
    "ACCOUNT_UPDATE": "account.update",
    "ACCOUNT_DELETE": "account.delete",
    "EXPORT_DATA": "export.data",
}

# ===============================
# CONFIGURAÇÕES DE EXPORT
# ===============================
EXPORT_CONFIG = {
    "PDF": {
        "extension": "pdf",
        "mime_type": "application/pdf",
        "max_rows": 10000,
    },
    "EXCEL": {
        "extension": "xlsx",
        "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "max_rows": 50000,
    },
    "CSV": {
        "extension": "csv",
        "mime_type": "text/csv",
        "max_rows": 100000,
    },
}

# ===============================
# REGEX PATTERNS
# ===============================
PATTERNS = {
    "EMAIL": r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    "CPF": r'^\d{3}\.\d{3}\.\d{3}-\d{2}$',
    "CNPJ": r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$',
    "PHONE": r'^\(\d{2}\) \d{4,5}-\d{4}$',
    "HEX_COLOR": r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$',
}
