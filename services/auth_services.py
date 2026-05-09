"""
Serviço de autenticação e autorização.
"""
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from config.security import (
    hash_password,
    verify_password,
    create_access_token,
)
from config.settings import settings
from config.logging_config import app_logger
from database.repositories.user_repo import UserRepository
from database.models.user import User
from schemas.user_schema import UserCreate, UserLogin
from schemas.common import TokenResponse
from utils.exceptions import (
    InvalidCredentialsError,
    EmailAlreadyExistsError,
    UserNotFoundError,
    AuthenticationError,
    InvalidPasswordError,
)
from utils.validators import is_valid_password
from middleware.rate_limiter import rate_limiter
from middleware.audit_log import audit_log


class AuthService:
    """
    Serviço responsável por autenticação e autorização.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
    
    def register_user(self, data: UserCreate) -> User:
        """
        Registra novo usuário.
        """
        # Verifica se email já existe
        if self.user_repo.email_exists(data.email):
            app_logger.warning(f"Tentativa de registro com email existente: {data.email}")
            raise EmailAlreadyExistsError()
        
        # Valida senha
        is_valid, error_msg = is_valid_password(data.password)
        if not is_valid:
            raise InvalidPasswordError(message=error_msg)
        
        # Hasheia senha
        password_hash = hash_password(data.password)
        
        # Cria usuário
        user = self.user_repo.create_user(
            name=data.name,
            email=data.email,
            password_hash=password_hash,
        )
        
        app_logger.info(f"Novo usuário registrado: {user.id} - {user.email}")
        audit_log.log_action(
            action="user.register",
            user_id=user.id,
            details={"email": user.email, "name": user.name}
        )
        
        return user
    
    def authenticate_user(self, data: UserLogin) -> TokenResponse:
        """
        Autentica usuário e retorna token JWT.
        """
        # Verifica rate limit de login
        allowed, retry_after = rate_limiter.check_login_attempts(data.email)
        if not allowed:
            app_logger.warning(f"Rate limit de login excedido: {data.email}")
            raise AuthenticationError(
                message=f"Muitas tentativas de login. Tente novamente em {retry_after} segundos.",
                code="RATE_LIMIT_LOGIN",
            )
        
        # Busca usuário
        user = self.user_repo.get_by_email(data.email)
        
        if not user:
            rate_limiter.record_login_attempt(data.email)
            app_logger.warning(f"Tentativa de login com email inexistente: {data.email}")
            raise InvalidCredentialsError()
        
        # Verifica senha
        if not verify_password(data.password, user.password_hash):
            rate_limiter.record_login_attempt(data.email)
            app_logger.warning(f"Tentativa de login com senha incorreta: {data.email}")
            audit_log.log_login(user.id, user.email, success=False)
            raise InvalidCredentialsError()
        
        # Verifica se usuário está ativo
        if not user.is_active:
            app_logger.warning(f"Tentativa de login de usuário inativo: {data.email}")
            raise AuthenticationError(
                message="Usuário inativo. Entre em contato com o suporte.",
                code="USER_INACTIVE",
            )
        
        # Limpa tentativas de login
        rate_limiter.clear_login_attempts(data.email)
        
        # Atualiza último login
        self.user_repo.update_last_login(user.id)
        
        # Gera tokens
        access_token = create_access_token({"sub": str(user.id)})
        
        app_logger.info(f"Login bem-sucedido: {user.id} - {user.email}")
        audit_log.log_login(user.id, user.email, success=True)
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=user.id,
            email=user.email,
        )
