"""
Configurações da aplicação carregadas de variáveis de ambiente.
"""
import os
from pathlib import Path

# Tenta importar do pydantic v2, senão usa v1
try:
    from pydantic_settings import BaseSettings
    from pydantic import ConfigDict, field_validator
    PYDANTIC_V2 = True
except ImportError:
    from pydantic import BaseSettings, validator
    PYDANTIC_V2 = False

# Carrega .env se existir
from dotenv import load_dotenv
load_dotenv()


class Settings(BaseSettings):
    """
    Configurações da aplicação usando Pydantic Settings.
    Valores são carregados de variáveis de ambiente ou .env
    """
    
    # ===============================
    # APLICAÇÃO
    # ===============================
    APP_NAME: str = "Sistema Financeiro Pessoal"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    # P0 (segredos): DEBUG default False. Ativar só via env explícito em dev.
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8050
    
    # ===============================
    # BANCO DE DADOS
    # ===============================
    DATABASE_URL: str = "sqlite:///./data/finance.db"
    
    # ===============================
    # SEGURANÇA
    # ===============================
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_SECRET_KEY: str = "dev-jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # P0 (Fase 8): reset curto e de uso único (padrão fintech 15 min).
    RESET_TOKEN_EXPIRE_MINUTES: int = 15
    
    # ===============================
    # LOGS
    # ===============================
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "detailed"
    LOG_FILE: str = "logs/app.log"
    AUDIT_LOG_FILE: str = "logs/audit.log"
    
    # ===============================
    # RATE LIMITING
    # ===============================
    RATE_LIMIT_LOGIN_ATTEMPTS: int = 5
    RATE_LIMIT_WINDOW_SECONDS: int = 300
    # P1 segurança: buckets por IP + HTTP global (Dash).
    RATE_LIMIT_LOGIN_PER_IP: int = 30
    RATE_LIMIT_REGISTER_PER_HOUR: int = 20
    RATE_LIMIT_HTTP_PER_MINUTE: int = 300
    RATE_LIMIT_HTTP_ENABLED: bool = True
    
    # ===============================
    # FEATURES
    # ===============================
    ENABLE_REGISTRATION: bool = True
    ENABLE_EMAIL_VERIFICATION: bool = False
    ENABLE_PASSWORD_RESET: bool = True
    AUDIT_ENABLED: bool = True
    
    # ===============================
    # VALIDAÇÃO CRÍTICA PARA DEPLOY
    # ===============================
    if PYDANTIC_V2:
        @field_validator("DATABASE_URL")
        @classmethod
        def assemble_db_connection(cls, v: str) -> str:
            """Corrige string de conexão do Render/Heroku para SQLAlchemy."""
            if v and v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql://", 1)
            return v
    else:
        @validator("DATABASE_URL", pre=True)
        def assemble_db_connection(cls, v: str) -> str:
            """Corrige string de conexão do Render/Heroku para SQLAlchemy."""
            if v and v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql://", 1)
            return v

    # Config para Pydantic v2
    if PYDANTIC_V2:
        model_config = ConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=True,
            extra="ignore",
        )
    else:
        # Config para Pydantic v1
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            case_sensitive = True
            extra = "ignore"

    if PYDANTIC_V2:
        @field_validator("SECRET_KEY", "JWT_SECRET_KEY")
        @classmethod
        def _no_default_secrets_in_prod(cls, v: str) -> str:
            """Fail-fast: segredo default de dev nunca sobe em produção."""
            env = os.getenv("ENVIRONMENT", "development")
            defaults = (
                "dev-secret-key-change-in-production",
                "dev-jwt-secret-key-change-in-production",
            )
            if env == "production" and (v in defaults or len(v) < 32):
                raise ValueError(
                    "SECRET_KEY/JWT_SECRET_KEY inseguros para ENVIRONMENT=production. "
                    "Defina valores longos e aleatórios via variáveis de ambiente."
                )
            return v


# Cria diretórios necessários automaticamente
try:
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
except Exception:
    pass # Em ambientes read-only ou cloud, isso pode falhar silenciosamente

# Instância global das configurações
settings = Settings()
