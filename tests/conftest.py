"""Configuracao de fixtures compartilhadas para os testes pytest.

SQLite :memory: — isolamento total, sem efeito no banco de desenvolvimento.
Valores Decimal em campos monetários (nunca float — ADR-002).
"""
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from database.base import Base

# Importa todos os models para que o Base.metadata os reconheca
# (imports aparentemente não usados registram as tabelas — noqa F401)
from database.models.user import User
from database.models.account import Account
from database.models.category import Category, TransactionType
from database.models.transaction import Transaction  # noqa: F401
from database.models.goal import Goal, GoalStatus, GoalCategory  # noqa: F401
from database.models.scheduled_bill import (  # noqa: F401
    ScheduledBill, BillType, BillStatus, BillRecurrence,
)
from database.models.password_reset_token import PasswordResetToken  # noqa: F401
from database.models.rate_limit import RateLimitHit  # noqa: F401
from database.models.refresh_token import RefreshToken  # noqa: F401


@pytest.fixture(scope="function")
def db_engine():
    """Cria um engine SQLite in-memory para cada funcao de teste."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db(db_engine) -> Session:
    """Fornece uma Session do banco in-memory com rollback automatico apos cada teste."""
    SessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def mem_factory(db_engine):
    """Factory de sessões :memory: p/ subsistemas com engine própria."""
    return sessionmaker(bind=db_engine, autocommit=False, autoflush=False)


@pytest.fixture
def isolated_limiter(mem_factory, monkeypatch):
    """Redireciona TODO o I/O do rate limiter p/ :memory: (não toca o dev DB)."""
    from middleware import rate_limiter as rl

    monkeypatch.setattr(rl, "SessionLocal", mem_factory)
    return mem_factory


@pytest.fixture
def sample_user(db: Session) -> User:
    """Cria e persiste um usuario padrao para reuso nos testes."""
    user = User(
        name="Teste Usuario",
        email="teste@email.com",
        password_hash="hashed_password",
        is_active=True,
        is_deleted=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_account(db: Session, sample_user: User) -> Account:
    """Cria e persiste uma conta bancaria padrao."""
    account = Account(
        user_id=sample_user.id,
        name="Conta Corrente",
        balance=Decimal("5000.00"),
        initial_balance=Decimal("5000.00"),
        is_active=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture
def sample_category(db: Session, sample_user: User) -> Category:
    """Cria e persiste uma categoria de despesa padrao."""
    category = Category(
        user_id=sample_user.id,
        name="Alimentacao",
        transaction_type=TransactionType.EXPENSE,
        is_system=False,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
