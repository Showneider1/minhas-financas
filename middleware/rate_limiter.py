"""
Sistema de rate limiting para proteção contra ataques de força bruta.

BUG 5 CORRIGIDO: versão anterior usava Dict em memória — zerado a cada
restart do processo e ineficaz em ambientes multi-worker (Gunicorn).

Esta versão persiste as tentativas em uma tabela SQLite dedicada
(login_attempts), mantendo o rate limit consistente entre restarts
e múltiplos workers, sem precisar de Redis ou dependência externa.

A assinatura pública dos métodos é idêntica à versão anterior:
    check_login_attempts(email)  → Tuple[bool, int]
    record_login_attempt(email)  → None
    clear_login_attempts(email)  → None

auth_services.py não precisa de nenhuma alteração.
"""
from datetime import datetime, timedelta, timezone
from typing import Tuple
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import Session
from database.base import Base
from database.connection import engine, SessionLocal
from config.settings import settings


# ──────────────────────────────────────────────────────────────────────────
# MODEL — tabela dedicada para tentativas de login
# Separada do User para evitar locking e facilitar limpeza/expiração.
# ──────────────────────────────────────────────────────────────────────────
class LoginAttempt(Base):
    """Registro de tentativas de login para rate limiting persistido."""
    __tablename__ = "login_attempts"

    id           = Column(Integer,  primary_key=True, index=True)
    email        = Column(String(100), nullable=False, index=True)
    attempted_at = Column(DateTime(timezone=True), nullable=False)


def _ensure_table():
    """Cria a tabela login_attempts se não existir (idempotente)."""
    LoginAttempt.__table__.create(bind=engine, checkfirst=True)


# Garante a tabela na importação do módulo
_ensure_table()


class RateLimiter:
    """
    Rate limiter com persistência em banco de dados.

    Estratégia sliding window: conta apenas tentativas dentro da
    janela de tempo configurada em RATE_LIMIT_WINDOW_SECONDS.
    """

    def _get_session(self) -> Session:
        return SessionLocal()

    def check_login_attempts(self, email: str) -> Tuple[bool, int]:
        """
        Verifica se o email excedeu o limite de tentativas de login.

        Returns:
            Tupla (permitido: bool, retry_after_segundos: int)
        """
        db = self._get_session()
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(
                seconds=settings.RATE_LIMIT_WINDOW_SECONDS
            )

            # Remove tentativas expiradas do email (limpeza oportunista)
            db.query(LoginAttempt).filter(
                LoginAttempt.email == email,
                LoginAttempt.attempted_at < cutoff,
            ).delete(synchronize_session=False)
            db.commit()

            # Conta tentativas válidas na janela atual
            attempts = (
                db.query(LoginAttempt)
                .filter(
                    LoginAttempt.email == email,
                    LoginAttempt.attempted_at >= cutoff,
                )
                .order_by(LoginAttempt.attempted_at.asc())
                .all()
            )

            count = len(attempts)
            if count >= settings.RATE_LIMIT_LOGIN_ATTEMPTS:
                oldest = attempts[0].attempted_at
                # Garante comparação timezone-aware
                if oldest.tzinfo is None:
                    oldest = oldest.replace(tzinfo=timezone.utc)
                retry_after = int(
                    (
                        oldest
                        + timedelta(seconds=settings.RATE_LIMIT_WINDOW_SECONDS)
                        - datetime.now(timezone.utc)
                    ).total_seconds()
                )
                return False, max(0, retry_after)

            return True, 0

        finally:
            db.close()

    def record_login_attempt(self, email: str) -> None:
        """Persiste uma tentativa de login no banco."""
        db = self._get_session()
        try:
            attempt = LoginAttempt(
                email=email,
                attempted_at=datetime.now(timezone.utc),
            )
            db.add(attempt)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def clear_login_attempts(self, email: str) -> None:
        """Remove todas as tentativas de login do email (após login bem-sucedido)."""
        db = self._get_session()
        try:
            db.query(LoginAttempt).filter(
                LoginAttempt.email == email
            ).delete(synchronize_session=False)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def cleanup_expired(self) -> int:
        """
        Remove TODAS as tentativas expiradas do banco (manutenção global).
        Chame periodicamente se quiser manter a tabela enxuta.
        Retorna o número de registros removidos.
        """
        db = self._get_session()
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(
                seconds=settings.RATE_LIMIT_WINDOW_SECONDS
            )
            deleted = (
                db.query(LoginAttempt)
                .filter(LoginAttempt.attempted_at < cutoff)
                .delete(synchronize_session=False)
            )
            db.commit()
            return deleted
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


# Instância global — mesma interface pública da versão anterior.
# auth_services.py não precisa de nenhuma alteração.
rate_limiter = RateLimiter()
