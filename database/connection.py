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
print(f"🗄️  DATABASE_URL: {settings.DATABASE_URL}")
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
    print("🔵 Sessão do banco ABERTA")
    try:
        yield db
        print("🟢 Executando COMMIT...")
        db.commit()
        print("✅ COMMIT realizado com sucesso!")
    except Exception as e:
        print(f"🔴 Erro na sessão - executando ROLLBACK: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise e
    finally:
        print("🔵 Fechando sessão do banco")
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
