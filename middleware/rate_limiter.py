"""
Sistema de rate limiting persistido (P0 login por email + P1 buckets por IP).

Duas camadas, mesma tabela de filosofia:
- Legado: `login_attempts` por email (sliding window) — mantido.
- P1: `rate_limit_hits(scope, key)` genérico thread-safe para buckets por IP
  (login, registro, reset) e para o hook HTTP do Dash.
Sem Redis por decisão (stack SQLite síncrona; ver ADR).
"""

import threading
from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import Session

from config.settings import settings
from database.base import Base
from database.connection import SessionLocal, engine
from database.models.rate_limit import RateLimitHit


# ──────────────────────────────────────────────────────────────────────────
# MODEL — tabela dedicada para tentativas de login
# Separada do User para evitar locking e facilitar limpeza/expiração.
# ──────────────────────────────────────────────────────────────────────────
class LoginAttempt(Base):
    """Registro de tentativas de login para rate limiting persistido."""

    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), nullable=False, index=True)
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

    def check_login_attempts(self, email: str) -> tuple[bool, int]:
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
            db.query(LoginAttempt).filter(LoginAttempt.email == email).delete(
                synchronize_session=False
            )
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

_lock = threading.Lock()


def hit(
    scope: str, key: str, limit: int, window_seconds: int, _session_factory=None
) -> tuple[bool, int]:
    """Registra tentativa no bucket (scope, key) com lock (P1).

    Atômico na prática para o servidor síncrono: limpa expirados, conta,
    e só insere se abaixo do limite. Retorna (permitido, retry_after_s).
    `_session_factory` existe só para testes isolados (produção omite).
    """
    key = (key or "unknown")[:200]
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=window_seconds)
    make_session = _session_factory or SessionLocal
    with _lock:
        db = make_session()
        try:
            db.query(RateLimitHit).filter(
                RateLimitHit.scope == scope,
                RateLimitHit.key == key,
                RateLimitHit.attempted_at < cutoff,
            ).delete(synchronize_session=False)
            rows = (
                db.query(RateLimitHit)
                .filter(
                    RateLimitHit.scope == scope,
                    RateLimitHit.key == key,
                    RateLimitHit.attempted_at >= cutoff,
                )
                .order_by(RateLimitHit.attempted_at.asc())
                .all()
            )
            if len(rows) >= limit:
                oldest = rows[0].attempted_at
                if oldest.tzinfo is None:
                    oldest = oldest.replace(tzinfo=timezone.utc)
                retry = int((oldest + timedelta(seconds=window_seconds) - now).total_seconds())
                db.commit()
                return False, max(0, retry)
            db.add(RateLimitHit(scope=scope, key=key, attempted_at=now))
            db.commit()
            return True, 0
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


def client_ip() -> str:
    """IP do cliente no contexto Flask/Dash (fallbacks seguros)."""
    try:
        from flask import has_request_context, request

        if has_request_context():
            forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
            # X-Forwarded-For só é confiável atrás de proxy próprio; usa o
            # primeiro IP mas sempre ancora no remote_addr para auditoria.
            if forwarded and request.remote_addr in ("127.0.0.1", "::1"):
                return forwarded[:45]
            return (request.remote_addr or "unknown")[:45]
    except Exception:
        pass
    return "unknown"
