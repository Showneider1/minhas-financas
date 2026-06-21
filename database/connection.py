"""
Gerenciamento de conexão com banco de dados.
"""
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config.settings import settings
from typing import Generator
import logging

logger = logging.getLogger(__name__)

# Cria engine
logger.info(f"Configurando DATABASE_URL: {settings.DATABASE_URL}")
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager para sessões do banco.
    
    Uso:
        with get_db_session() as db:
            # use db aqui
    """
    db = SessionLocal()
    logger.debug("Sessão do banco ABERTA")
    try:
        yield db
        logger.debug("Executando COMMIT...")
        db.commit()
        logger.debug("COMMIT realizado com sucesso!")
    except Exception as e:
        logger.error(f"Erro na sessão - executando ROLLBACK: {e}", exc_info=True)
        db.rollback()
        raise  # Mantém o stack trace intacto repassando a exceção original
    finally:
        logger.debug("Fechando sessão do banco")
        db.close()


def init_db():
    """
    Inicializa o banco de dados criando todas as tabelas.
    """
    from database.base import Base
    import database.models.user
    import database.models.account
    import database.models.category
    import database.models.transaction
    
    Base.metadata.create_all(bind=engine)
