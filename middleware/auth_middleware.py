"""
Middleware de autenticação e autorização.
"""
from functools import wraps
from typing import Optional
from config.security import verify_token
from config.logging_config import app_logger
from utils.exceptions import AuthenticationError


def require_auth(f):
    """
    Decorator para endpoints que requerem autenticação.
    Verifica token JWT e extrai user_id.
    
    Uso:
        @require_auth
        def minha_funcao(user_id, ...):
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Tenta pegar token do contexto (headers, etc)
        token = get_token_from_request()
        
        if not token:
            app_logger.warning("Tentativa de acesso sem token")
            raise AuthenticationError("Token não fornecido")
        
        # Verifica e decodifica token
        user_id = verify_token(token)
        
        if not user_id:
            app_logger.warning("Token inválido ou expirado")
            raise AuthenticationError("Token inválido ou expirado")
        
        # Passa user_id para a função
        return f(user_id=user_id, *args, **kwargs)
    
    return decorated_function


def get_token_from_request() -> Optional[str]:
    """
    Extrai token JWT da requisição.
    
    Returns:
        Token ou None
    """
    # Em Dash, usamos dcc.Store para armazenar o token
    # Esta função é mais útil em contextos de API REST
    # Para Dash, o token é gerenciado pelos callbacks
    return None


def get_current_user(token: str) -> Optional[int]:
    """
    Retorna user_id do token.
    
    Args:
        token: Token JWT
    
    Returns:
        User ID ou None
    """
    return verify_token(token)


def check_auth(auth_data: dict) -> bool:
    """
    Verifica se usuário está autenticado.
    
    Args:
        auth_data: Dados de autenticação do store
    
    Returns:
        True se autenticado
    """
    if not auth_data:
        return False
    
    token = auth_data.get("token")
    if not token:
        return False
    
    user_id = verify_token(token)
    return user_id is not None
