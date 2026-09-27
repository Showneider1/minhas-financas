"""
Contexto de autenticação para callbacks Dash (P0 — Fase 7, anti-IDOR).

REGRA DURA: nunca confie em `user_id` enviado pelo frontend (`store-user-id`
é espelho legível via DevTools). O usuário é derivado EXCLUSIVAMENTE do JWT
em `auth-store` via `verify_token()`.

Uso em todo callback que toca dados:
    from middleware.auth_context import resolve_user
    user_id = resolve_user(auth_data)  # levanta AuthenticationError se inválido
    # opcional: resolve_user(auth_data, claimed_user_id) rejeita mismatch.
"""
from typing import Any, Dict, Optional

from config.security import verify_token
from utils.exceptions import AuthenticationError


def resolve_user(auth_data: Optional[Dict[str, Any]],
                 claimed_user_id: Optional[int] = None) -> int:
    """Extrai user_id do JWT; rejeita ausente/expirado/adulterado e mismatch.

    Args:
        auth_data: conteúdo do dcc.Store auth-store (dict com "token").
        claimed_user_id: valor alegado pelo frontend (store-user-id); se
            presente e divergente do token, rejeita (possível forja).

    Returns:
        user_id autenticado (int).

    Raises:
        AuthenticationError: token ausente/inválido/expirado ou mismatch.
    """
    token = (auth_data or {}).get("token") if isinstance(auth_data, dict) else None
    if not token:
        raise AuthenticationError("Sessão ausente — faça login novamente.")
    user_id = verify_token(token)
    if user_id is None:
        raise AuthenticationError("Sessão inválida ou expirada — faça login novamente.")
    if claimed_user_id is not None:
        try:
            claimed = int(claimed_user_id)
        except (TypeError, ValueError):
            raise AuthenticationError("Identificador de usuário inválido.")
        if claimed != user_id:
            raise AuthenticationError("Divergência de sessão — faça login novamente.")
    return user_id
