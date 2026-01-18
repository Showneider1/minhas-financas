"""
Exceções customizadas da aplicação.
"""


class AppException(Exception):
    """
    Exceção base da aplicação.
    """
    
    def __init__(self, message: str = "Erro na aplicação", code: str = "APP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class ValidationError(AppException):
    """Erro de validação de dados."""
    
    def __init__(self, message: str = "Erro de validação", field: str = None):
        super().__init__(message=message, code="VALIDATION_ERROR")
        self.field = field


class AuthenticationError(AppException):
    """Erro de autenticação."""
    
    def __init__(self, message: str = "Erro de autenticação", code: str = "AUTH_ERROR"):
        super().__init__(message=message, code=code)


class InvalidCredentialsError(AuthenticationError):
    """Credenciais inválidas."""
    
    def __init__(self):
        super().__init__(
            message="Email ou senha incorretos",
            code="INVALID_CREDENTIALS"
        )


class EmailAlreadyExistsError(AppException):
    """Email já cadastrado."""
    
    def __init__(self):
        super().__init__(
            message="Este email já está cadastrado",
            code="EMAIL_EXISTS"
        )


class UserNotFoundError(AppException):
    """Usuário não encontrado."""
    
    def __init__(self):
        super().__init__(
            message="Usuário não encontrado",
            code="USER_NOT_FOUND"
        )


class InvalidPasswordError(AppException):
    """Senha inválida."""
    
    def __init__(self, message: str = "Senha inválida"):
        super().__init__(
            message=message,
            code="INVALID_PASSWORD"
        )


class AccountNotFoundError(AppException):
    """Conta não encontrada."""
    
    def __init__(self):
        super().__init__(
            message="Conta não encontrada",
            code="ACCOUNT_NOT_FOUND"
        )


class CategoryNotFoundError(AppException):
    """Categoria não encontrada."""
    
    def __init__(self):
        super().__init__(
            message="Categoria não encontrada",
            code="CATEGORY_NOT_FOUND"
        )


class TransactionNotFoundError(AppException):
    """Transação não encontrada."""
    
    def __init__(self):
        super().__init__(
            message="Transação não encontrada",
            code="TRANSACTION_NOT_FOUND"
        )


class InvalidAmountError(AppException):
    """Valor inválido."""
    
    def __init__(self):
        super().__init__(
            message="Valor deve ser maior que zero",
            code="INVALID_AMOUNT"
        )


class BusinessError(AppException):
    """Erro de regra de negócio."""
    
    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="BUSINESS_ERROR"
        )


class DatabaseError(AppException):
    """Erro de banco de dados."""
    
    def __init__(self, message: str = "Erro ao acessar banco de dados"):
        super().__init__(
            message=message,
            code="DATABASE_ERROR"
        )
