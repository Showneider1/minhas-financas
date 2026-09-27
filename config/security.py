"""
Funções de segurança: hash de senhas, JWT tokens, etc.
"""
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from config.settings import settings


# ──────────────────────────────────────────────────────────────────
# BUG 8 CORRIGIDO (security.py): todas as chamadas a datetime.utcnow()
# foram substituídas por datetime.now(timezone.utc), retornando objetos
# timezone-aware compatíveis com Python 3.12+.
# ──────────────────────────────────────────────────────────────────


# ===============================
# PASSWORD HASHING
# ===============================

def hash_password(password: str) -> str:
    """Gera hash bcrypt da senha."""
    salt   = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """Verifica se a senha corresponde ao hash armazenado."""
    return bcrypt.checkpw(
        password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ===============================
# JWT TOKENS
# ===============================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria JWT access token."""
    to_encode = data.copy()
    expire    = datetime.now(timezone.utc) + (
        expires_delta if expires_delta
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({
        "exp":  expire,
        "iat":  datetime.now(timezone.utc),
        "type": "access",
    })
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Cria JWT refresh token (vida mais longa, com `jti` para denylist)."""
    import uuid

    to_encode = data.copy()
    to_encode.setdefault("jti", str(uuid.uuid4()))
    expire    = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp":  expire,
        "iat":  datetime.now(timezone.utc),
        "type": "refresh",
    })
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[Dict]:
    """Decodifica e valida JWT token. Retorna payload ou None se inválido."""
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def verify_token(token: str) -> Optional[int]:
    """Verifica token e retorna user_id (int) ou None se inválido."""
    payload = decode_token(token)
    if not payload:
        return None
    if payload.get("type") != "access":
        return None
    user_id = payload.get("sub")
    if user_id:
        try:
            return int(user_id)
        except (ValueError, TypeError):
            return None
    return None


def generate_password_reset_token(user_id: int) -> str:
    """Gera token para reset de senha (uso único, expiração curta).

    P0 (Fase 8): separação absoluta do access token.
    - NÃO reutiliza create_access_token() (que sobrescreveria `type`).
    - Inclui `jti` (UUID v4): o consumo deve registrar o `jti` em
      `password_reset_tokens` e negar reuso (ver consume_password_reset_token).
    - Expiração: RESET_TOKEN_EXPIRE_MINUTES (15 min). Nunca autentica sessão:
      verify_token() rejeita `type != access`.

    NOTA: sem `db` aqui para não acoplar este módulo à sessão; a emissão com
    persistência usa `issue_password_reset_token(db, user_id)`.
    """
    import uuid

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.RESET_TOKEN_EXPIRE_MINUTES
    )
    to_encode = {
        "sub": str(user_id),
        "type": "password_reset",
        "jti": str(uuid.uuid4()),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def issue_password_reset_token(db, user_id: int) -> str:
    """Emite reset token persistindo o `jti` (uso único)."""
    from database.models.password_reset_token import PasswordResetToken

    token = generate_password_reset_token(user_id)
    payload = decode_token(token)
    # PyJWT devolve `exp` como timestamp numérico — converte para datetime.
    exp_ts = payload["exp"]
    expires_at = (
        exp_ts if isinstance(exp_ts, datetime)
        else datetime.fromtimestamp(int(exp_ts), tz=timezone.utc)
    )
    record = PasswordResetToken(
        jti=payload["jti"],
        user_id=user_id,
        expires_at=expires_at,
        used=False,
    )
    db.add(record)
    db.commit()
    return token


def _reset_record(db, payload) -> Optional[object]:
    """Busca registro do `jti` válido (não usado, não expirado)."""
    from database.models.password_reset_token import PasswordResetToken

    jti = payload.get("jti")
    if not jti:
        return None
    record = db.query(PasswordResetToken).filter(
        PasswordResetToken.jti == jti
    ).first()
    if not record or record.used:
        return None
    expires_at = record.expires_at
    if expires_at is not None:
        now = datetime.now(timezone.utc)
        exp = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
        if exp <= now:
            return None
    return record


def verify_password_reset_token(db, token: str) -> Optional[int]:
    """Valida reset token (tipo + assinatura + expiração + `jti` não usado).

    Retorna user_id ou None. NÃO marca como usado (ver consume_...).
    Nunca autentica sessão: use apenas no fluxo de recuperação.
    """
    payload = decode_token(token)
    if not payload:
        return None
    if payload.get("type") != "password_reset":
        return None
    record = _reset_record(db, payload)
    if not record:
        return None
    try:
        return int(payload.get("sub"))
    except (ValueError, TypeError):
        return None


def consume_password_reset_token(db, token: str) -> Optional[int]:
    """Consome reset token (marca `jti` como usado, atômico). Reuso negado."""
    payload = decode_token(token)
    if not payload or payload.get("type") != "password_reset":
        return None
    record = _reset_record(db, payload)
    if not record:
        return None
    try:
        user_id = int(payload.get("sub"))
    except (ValueError, TypeError):
        return None
    record.used = True
    db.commit()
    return user_id


def verify_refresh_token(token: str) -> Optional[int]:
    """Verifica refresh token e retorna user_id (só `type == refresh`).

    P0: separação absoluta — refresh nunca passa em verify_token e
    access/reset nunca passam aqui.
    """
    payload = decode_token(token)
    if not payload:
        return None
    if payload.get("type") != "refresh":
        return None
    user_id = payload.get("sub")
    if user_id:
        try:
            return int(user_id)
        except (ValueError, TypeError):
            return None
    return None


# ------------------------------------------------------------------
# Refresh rotation + denylist server-side (P1 — Fase 3)
# ------------------------------------------------------------------

def _refresh_expires_at(payload: dict):
    exp = payload.get("exp")
    if isinstance(exp, datetime):
        return exp
    return datetime.fromtimestamp(int(exp), tz=timezone.utc)


def issue_refresh_token(db, user_id: int) -> str:
    """Emite refresh persistindo o `jti` (sessão rastreável/revogável)."""
    from database.models.refresh_token import RefreshToken

    token = create_refresh_token({"sub": str(user_id)})
    payload = decode_token(token)
    db.add(RefreshToken(
        jti=payload["jti"],
        user_id=user_id,
        expires_at=_refresh_expires_at(payload),
        revoked=False,
    ))
    db.commit()
    return token


def verify_live_refresh_token(db, token: str) -> Optional[int]:
    """Refresh válido se: assinatura+tipo+expiração OK E `jti` vivo no servidor."""
    from database.models.refresh_token import RefreshToken

    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        return None
    row = db.query(RefreshToken).filter(
        RefreshToken.jti == payload.get("jti")
    ).first()
    if not row or row.revoked:
        return None
    try:
        return int(payload.get("sub"))
    except (ValueError, TypeError):
        return None


def revoke_all_refresh_tokens(db, user_id: int) -> int:
    """Revoga a árvore inteira de sessões do usuário (logout / roubo)."""
    from database.models.refresh_token import RefreshToken

    count = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked.is_(False),
        )
        .update({"revoked": True}, synchronize_session=False)
    )
    db.commit()
    return count


def refresh_session(db, refresh_token: str):
    """Rotação: valida o refresh vivo, revoga (replaced_by) e emite par novo.

    Reuso de token revogado/inexistente com assinatura válida = indício de
    roubo → revoga TODA a árvore do usuário e nega (401 semântico via
    AuthenticationError do chamador).
    """
    from database.models.refresh_token import RefreshToken
    from utils.exceptions import AuthenticationError

    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise AuthenticationError("Refresh token inválido.", code="INVALID_REFRESH")
    try:
        user_id = int(payload.get("sub"))
    except (ValueError, TypeError):
        raise AuthenticationError("Refresh token inválido.", code="INVALID_REFRESH")

    row = db.query(RefreshToken).filter(
        RefreshToken.jti == payload.get("jti")
    ).first()
    if not row or row.revoked:
        # Possível roubo: derruba todas as sessões do dono alegado.
        try:
            revoke_all_refresh_tokens(db, user_id)
        except Exception:
            db.rollback()
        raise AuthenticationError(
            "Sessão revogada — faça login novamente.", code="REVOKED_SESSION"
        )

    new_refresh = create_refresh_token({"sub": str(user_id)})
    new_payload = decode_token(new_refresh)
    try:
        db.add(RefreshToken(
            jti=new_payload["jti"],
            user_id=user_id,
            expires_at=_refresh_expires_at(new_payload),
            revoked=False,
        ))
        row.revoked = True
        row.replaced_by = new_payload["jti"]
        db.commit()
    except Exception:
        db.rollback()
        raise
    return create_access_token({"sub": str(user_id)}), new_refresh
