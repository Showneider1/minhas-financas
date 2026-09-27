"""Tokens de recuperação de senha — uso único (P0 — Fase 8).

Um `jti` (UUID v4) é gerado por reset solicitado e marcado como usado no
consumo. Reuso do mesmo token é negado mesmo dentro da expiração.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database.base import Base


def _utcnow():
    return datetime.now(timezone.utc)


class PasswordResetToken(Base):
    """Registro de token de reset (somente `jti`, nunca o token)."""

    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String(36), nullable=False, unique=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    user = relationship("User")
