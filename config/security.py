"""
Funções de segurança: hash de senhas, JWT tokens, etc.
"""
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from config.settings import settings


# ===============================
# PASSWORD HASHING
# ===============================

def hash_password(password: str) -> str:
    """
    Gera hash bcrypt da senha.
    
    Args:
        password: Senha em texto plano
    
    Returns:
        Hash da senha
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verifica se senha corresponde ao hash.
    
    Args:
        password: Senha em texto plano
        hashed_password: Hash armazenado
    
    Returns:
        True se senha correta
    """
    return bcrypt.checkpw(
        password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


# ===============================
# JWT TOKENS
# ===============================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria JWT access token.
    
    Args:
        data: Dados a encodar no token (ex: {"sub": "user_id"})
        expires_delta: Tempo de expiração customizado
    
    Returns:
        Token JWT
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Cria JWT refresh token (vida mais longa).
    
    Args:
        data: Dados a encodar
    
    Returns:
        Refresh token JWT
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict]:
    """
    Decodifica e valida JWT token.
    
    Args:
        token: Token JWT
    
    Returns:
        Payload do token ou None se inválido
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    
    except jwt.ExpiredSignatureError:
        # Token expirado
        return None
    
    except jwt.InvalidTokenError:
        # Token inválido
        return None


def verify_token(token: str) -> Optional[int]:
    """
    Verifica token e retorna user_id.
    
    Args:
        token: Token JWT
    
    Returns:
        User ID ou None se inválido
    """
    payload = decode_token(token)
    
    if not payload:
        return None
    
    # Verifica tipo
    if payload.get("type") != "access":
        return None
    
    # Extrai user_id
    user_id = payload.get("sub")
    if user_id:
        try:
            return int(user_id)
        except (ValueError, TypeError):
            return None
    
    return None


def generate_password_reset_token(user_id: int) -> str:
    """
    Gera token para reset de senha (válido por 1 hora).
    
    Args:
        user_id: ID do usuário
    
    Returns:
        Token de reset
    """
    data = {"sub": str(user_id), "type": "password_reset"}
    expire = timedelta(hours=1)
    return create_access_token(data, expire)


def verify_password_reset_token(token: str) -> Optional[int]:
    """
    Verifica token de reset e retorna user_id.
    
    Args:
        token: Token de reset
    
    Returns:
        User ID ou None se inválido
    """
    payload = decode_token(token)
    
    if not payload:
        return None
    
    # Verifica tipo
    if payload.get("type") != "password_reset":
        return None
    
    # Extrai user_id
    user_id = payload.get("sub")
    if user_id:
        try:
            return int(user_id)
        except (ValueError, TypeError):
            return None
    
    return None
