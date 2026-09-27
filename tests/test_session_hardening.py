"""Hardening de sessão — rotação, denylist e logout server-side.

- Rotação: refresh vivo → par novo; antigo morre.
- Reuso de revogado = roubo → árvore inteira revogada + 401.
- Logout revoga tudo; expirado/adulterado negado; access não rotaciona.
"""
from datetime import datetime, timedelta, timezone

import pytest

from config.security import (
    create_access_token,
    issue_refresh_token,
    refresh_session,
    verify_live_refresh_token,
)
from services.auth_services import AuthService
from schemas.user_schema import UserLogin
from utils.exceptions import AuthenticationError


def test_rotation_happy_path(db, sample_user):
    access, new_refresh = refresh_session(
        db, issue_refresh_token(db, sample_user.id))
    from config.security import verify_token

    assert verify_token(access) == sample_user.id
    assert verify_live_refresh_token(db, new_refresh) == sample_user.id


def test_old_refresh_dies_after_rotation(db, sample_user):
    old = issue_refresh_token(db, sample_user.id)
    _, new_refresh = refresh_session(db, old)
    # Antigo: morto.
    assert verify_live_refresh_token(db, old) is None
    # Novo: vivo.
    assert verify_live_refresh_token(db, new_refresh) == sample_user.id


def test_reuse_of_revoked_kills_tree_and_401(db, sample_user):
    old = issue_refresh_token(db, sample_user.id)
    _, new_refresh = refresh_session(db, old)
    # Atacante reusa o token já rotacionado (assinatura válida!):
    with pytest.raises(AuthenticationError) as exc:
        refresh_session(db, old)
    assert exc.value.code == "REVOKED_SESSION"
    # Árvore inteira morta — inclusive o token novo legítimo.
    assert verify_live_refresh_token(db, new_refresh) is None
    assert verify_live_refresh_token(db, old) is None


def test_logout_revokes_server_side(db, sample_user):
    svc = AuthService(db)
    r1 = issue_refresh_token(db, sample_user.id)
    r2 = issue_refresh_token(db, sample_user.id)
    assert verify_live_refresh_token(db, r1) == sample_user.id
    revoked = svc.logout(sample_user.id)
    assert revoked == 2
    assert verify_live_refresh_token(db, r1) is None
    assert verify_live_refresh_token(db, r2) is None
    # Rotação pós-logout nega (401).
    with pytest.raises(AuthenticationError):
        svc.refresh_session(r1)


def test_expired_and_tampered_refresh_denied(db, sample_user):
    import jwt
    from config import security as _sec

    payload = {
        "sub": str(sample_user.id),
        "type": "refresh",
        "jti": "expired-jti-0001",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        "iat": datetime.now(timezone.utc) - timedelta(days=8),
    }
    expired = jwt.encode(payload, _sec.settings.JWT_SECRET_KEY,
                         algorithm=_sec.settings.JWT_ALGORITHM)
    assert verify_live_refresh_token(db, expired) is None

    live = issue_refresh_token(db, sample_user.id)
    tampered = live[:-2] + ("aa" if not live.endswith("aa") else "bb")
    assert verify_live_refresh_token(db, tampered) is None


def test_access_token_cannot_rotate(db, sample_user):
    access = create_access_token({"sub": str(sample_user.id)})
    with pytest.raises(AuthenticationError):
        refresh_session(db, access)


def test_full_login_logout_cycle(db, isolated_limiter):
    """Ciclo real: registro → login (com refresh) → logout → refresh morto."""
    from schemas.user_schema import UserCreate

    svc = AuthService(db)
    svc.register_user(UserCreate(name="Ciclo Silva", email="ciclo@ex.com",
                                 password="Segura123"))
    token = svc.authenticate_user(
        UserLogin(email="ciclo@ex.com", password="Segura123"),
        client_ip="198.51.100.44")
    assert token.refresh_token
    assert verify_live_refresh_token(db, token.refresh_token) == token.user_id
    svc.logout(token.user_id)
    assert verify_live_refresh_token(db, token.refresh_token) is None
