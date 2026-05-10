"""
Modelo de Usuário.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database.base import Base


def _utcnow():
    """
    Retorna datetime atual em UTC com timezone-aware.

    ──────────────────────────────────────────────────────────────
    BUG 8 CORRIGIDO: datetime.utcnow() foi depreciado no Python
    3.12 e removido no 3.13. Substituído por datetime.now(timezone.utc)
    que retorna um objeto timezone-aware, evitando ambiguidades de
    timezone em comparações e serialização.
    ──────────────────────────────────────────────────────────────
    """
    return datetime.now(timezone.utc)


class User(Base):
    """Modelo de Usuário."""
    __tablename__ = "users"

    id            = Column(Integer,      primary_key=True, index=True)
    name          = Column(String(100),  nullable=False)
    email         = Column(String(100),  unique=True, nullable=False, index=True)
    password_hash = Column(String(255),  nullable=False)

    # Flags de sistema
    is_active   = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_deleted  = Column(Boolean, default=False)  # Soft delete

    # Timestamps (timezone-aware)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relacionamentos
    accounts     = relationship("Account",     back_populates="user", cascade="all, delete-orphan")
    categories   = relationship("Category",    back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    goals           = relationship("Goal",          back_populates="user", cascade="all, delete-orphan")
    scheduled_bills  = relationship("ScheduledBill", back_populates="user", cascade="all, delete-orphan")
    assets       = relationship("Asset",       back_populates="user", cascade="all, delete-orphan")
