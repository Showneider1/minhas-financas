"""
Serviço de autenticação e autorização.
"""
from typing import Optional
from sqlalchemy.orm import Session
from config.security import (
    hash_password,
    verify_password,
    verify_token,
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
    
    def register_user(self, data: UserCreate, client_ip: Optional[str] = None) -> User:
        """
        Registra novo usuário (com bucket anti-abuso por IP — P1).
        """
        from middleware.rate_limiter import hit as _hit

        allowed, retry = _hit(
            "register", f"ip:{client_ip or 'unknown'}",
            settings.RATE_LIMIT_REGISTER_PER_HOUR, 3600,
        )
        if not allowed:
            raise AuthenticationError(
                message="Muitas contas criadas a partir deste endereço. "
                        f"Tente novamente em {retry} segundos.",
                code="RATE_LIMIT_REGISTER",
            )
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
    
    def authenticate_user(self, data: UserLogin, client_ip: Optional[str] = None) -> TokenResponse:
        """
        Autentica usuário e retorna par access + refresh (P1: refresh persistido).
        Buckets: por email (legado) E por IP (anti-força-bruta distribuída).
        """
        from middleware.rate_limiter import hit as _hit
        from config.security import issue_refresh_token

        # Verifica rate limit de login (email + IP)
        allowed, retry_after = rate_limiter.check_login_attempts(data.email)
        if not allowed:
            app_logger.warning(f"Rate limit de login excedido: {data.email}")
            raise AuthenticationError(
                message=f"Muitas tentativas de login. Tente novamente em {retry_after} segundos.",
                code="RATE_LIMIT_LOGIN",
            )
        ip_allowed, ip_retry = _hit(
            "login", f"ip:{client_ip or 'unknown'}",
            settings.RATE_LIMIT_LOGIN_PER_IP, settings.RATE_LIMIT_WINDOW_SECONDS,
        )
        if not ip_allowed:
            raise AuthenticationError(
                message="Muitas tentativas a partir deste endereço. "
                        f"Tente novamente em {ip_retry} segundos.",
                code="RATE_LIMIT_LOGIN_IP",
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
        
        # Gera tokens (P1: refresh persistido p/ rotação/denylist server-side)
        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = issue_refresh_token(self.db, user.id)
        
        app_logger.info(f"Login bem-sucedido: {user.id} - {user.email}")
        audit_log.log_login(user.id, user.email, success=True)
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=user.id,
            email=user.email,
            name=user.name or "",
            refresh_token=refresh_token,
        )

    def refresh_session(self, refresh_token: str) -> TokenResponse:
        """Rotação de sessão: refresh vivo → par novo (P1)."""
        from config.security import refresh_session as _rotate

        access, new_refresh = _rotate(self.db, refresh_token)
        payload_user = self.user_repo.get_by_id(verify_token(access))
        return TokenResponse(
            access_token=access,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_id=payload_user.id if payload_user else 0,
            email=payload_user.email if payload_user else "",
            name=(payload_user.name if payload_user else "") or "",
            refresh_token=new_refresh,
        )

    def logout(self, user_id: int) -> int:
        """Logout server-side: revoga a árvore de refresh do usuário (P1)."""
        from config.security import revoke_all_refresh_tokens

        count = revoke_all_refresh_tokens(self.db, user_id)
        audit_log.log_action(
            action="user.logout", user_id=user_id,
            details={"revoked_refresh": count},
        )
        return count
