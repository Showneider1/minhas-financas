"""Refresh tokens persistidos — rotação e denylist (P1 segurança).

Cada sessão possui um refresh `jti` vivo. Rotação (`refresh_session`):
revoga o antigo (replaced_by) e emite par novo. Reuso de token revogado =
indício de roubo → revoga a árvore inteira do usuário.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database.base import Base


def _utcnow():
    return datetime.now(timezone.utc)


class RefreshToken(Base):
    """Registro de refresh token (somente `jti`, nunca o JWT)."""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String(36), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    replaced_by = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    user = relationship("User")
