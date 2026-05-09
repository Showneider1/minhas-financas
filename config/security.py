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
    """Cria JWT refresh token (vida mais longa)."""
    to_encode = data.copy()
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
    """Gera token para reset de senha (válido por 1 hora)."""
    data   = {"sub": str(user_id), "type": "password_reset"}
    expire = timedelta(hours=1)
    return create_access_token(data, expire)


def verify_password_reset_token(token: str) -> Optional[int]:
    """Verifica token de reset e retorna user_id ou None."""
    payload = decode_token(token)
    if not payload:
        return None
    if payload.get("type") != "password_reset":
        return None
    user_id = payload.get("sub")
    if user_id:
        try:
            return int(user_id)
        except (ValueError, TypeError):
            return None
    return None
