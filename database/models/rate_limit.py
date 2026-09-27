"""Model de hits de rate limiting (P1 segurança).

Tabela operacional genérica para buckets sliding-window por (scope, key),
ex.: ("login", "ip:1.2.3.4"), ("register", "ip:1.2.3.4").
Criada via Alembic; nunca versionada como dado de negócio.
"""
from sqlalchemy import Column, Integer, String, DateTime, Index
from datetime import datetime, timezone
from database.base import Base


def _utcnow():
    return datetime.now(timezone.utc)


class RateLimitHit(Base):
    """Registro de tentativa para rate limiting persistido."""

    __tablename__ = "rate_limit_hits"

    id = Column(Integer, primary_key=True, index=True)
    scope = Column(String(50), nullable=False)
    key = Column(String(200), nullable=False)
    attempted_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    __table_args__ = (
        Index("ix_ratelimit_scope_key_at", "scope", "key", "attempted_at"),
    )
