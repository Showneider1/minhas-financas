"""Tokens — separação absoluta access/refresh/reset (Missão 2 Fase 8).

- Reset: uso único (jti), expiração curta, nunca autentica sessão.
- Refresh: só passa em verify_refresh_token; access só em verify_token.
- Testes negativos nos 6 sentidos + reuso negado + adulterado negado.
"""
from config import security
from config.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    verify_refresh_token,
    issue_password_reset_token,
    verify_password_reset_token,
    consume_password_reset_token,
)


def test_cross_type_matrix(db):
    access = create_access_token({"sub": "7"})
    refresh = create_refresh_token({"sub": "7"})
    reset = issue_password_reset_token(db, 7)

    assert verify_token(access) == 7
    assert verify_token(refresh) is None
    assert verify_token(reset) is None

    assert verify_refresh_token(refresh) == 7
    assert verify_refresh_token(access) is None
    assert verify_refresh_token(reset) is None

    assert verify_password_reset_token(db, access) is None
    assert verify_password_reset_token(db, refresh) is None
    assert verify_password_reset_token(db, reset) == 7


def test_reset_single_use(db):
    reset = issue_password_reset_token(db, 9)
    assert verify_password_reset_token(db, reset) == 9
    assert consume_password_reset_token(db, reset) == 9
    # Reuso negado (verificação e consumo).
    assert verify_password_reset_token(db, reset) is None
    assert consume_password_reset_token(db, reset) is None
    # E nunca virou sessão.
    assert verify_token(reset) is None


def test_tampered_and_wrong_type_denied(db):
    access = create_access_token({"sub": "7"})
    tampered = access[:-2] + ("aa" if not access.endswith("aa") else "bb")
    assert verify_token(tampered) is None
    assert verify_token("") is None
    assert verify_token(None) is None
    assert verify_refresh_token(None) is None
    assert verify_password_reset_token(db, "not-a-token") is None


def test_reset_expired_denied(db):
    from datetime import datetime, timedelta, timezone
    import jwt

    # Token com exp no passado (assinatura válida) — deve negar.
    payload = {
        "sub": "11",
        "type": "password_reset",
        "jti": "expired-jti-0000",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        "iat": datetime.now(timezone.utc) - timedelta(minutes=20),
    }
    token = jwt.encode(payload, security.settings.JWT_SECRET_KEY,
                       algorithm=security.settings.JWT_ALGORITHM)
    assert verify_password_reset_token(db, token) is None
    assert consume_password_reset_token(db, token) is None
