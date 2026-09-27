"""
Gerenciamento de conexão com banco de dados.
"""
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config.settings import settings
from typing import Generator
import logging

# Configuração de logger específico para o módulo de banco de dados
logger = logging.getLogger("database.connection")


def _mask_db_url(url: str) -> str:
    """Masca senha da URL para logs (nunca expor credencial)."""
    try:
        from urllib.parse import urlsplit, urlunsplit
        parts = urlsplit(url)
        if parts.password:
            netloc = parts.hostname or ""
            if parts.username:
                netloc = f"{parts.username}:***@{netloc}"
            if parts.port:
                netloc = f"{netloc}:{parts.port}"
            return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    except Exception:
        pass
    return url.split("@")[-1] if "@" in url else url

# Cria engine
logger.info(f"🗄️  Inicializando conexão com DB: {_mask_db_url(settings.DATABASE_URL)}")

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=settings.DEBUG and "sqlite" not in settings.DATABASE_URL, # Echo apenas se debug e não sqlite (muito verboso)
    pool_pre_ping=True # Garante reconexão automática se a conexão cair
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager para sessões do banco.
    Garante commit em caso de sucesso e rollback em caso de erro.
    
    Uso:
        with get_db_session() as db:
            repo = UserRepo(db)
            repo.create(...)
    """
    db = SessionLocal()
    # logger.debug("🔵 Sessão do banco ABERTA") # Debug level para não poluir prod
    try:
        yield db
        # logger.debug("🟢 Executando COMMIT...")
        db.commit()
    except Exception as e:
        logger.error(f"🔴 Erro na sessão - executando ROLLBACK. Erro: {str(e)}", exc_info=True)
        db.rollback()
        raise e
    finally:
        # logger.debug("🔵 Fechando sessão do banco")
        db.close()


def init_db():
    """
    Inicializa o banco de dados criando todas as tabelas.

    SEGURO: apenas `create_all` (cria o que falta, nunca apaga/alterada nada).
    Nunca chamar `drop_all` aqui. Importações locais para evitar ciclos.
    """
    try:
        # Importar modelos aqui para garantir que o SQLAlchemy os conheça antes do create_all
        from database.base import Base
        # Imports explícitos para garantir o registro no Metadata
        # (todos os models — goals/scheduled_bills/investment ficavam de fora e
        #  nunca tinham tabela física criada; aditivo, não apaga nada)
        import database.models.user
        import database.models.account
        import database.models.category
        import database.models.transaction
        import database.models.budget
        import database.models.goal
        import database.models.scheduled_bill
        import database.models.investment
        import database.models.password_reset_token  # noqa: F401 — registro no metadata
        
        logger.info("Recriando/Verificando tabelas do banco de dados...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tabelas verificadas/criadas com sucesso.")
        
    except ImportError as e:
        logger.critical(f"Erro fatal ao importar modelos para inicialização do DB: {e}")
        raise
    except Exception as e:
        logger.critical(f"Erro fatal ao inicializar o banco de dados: {e}")
        raise