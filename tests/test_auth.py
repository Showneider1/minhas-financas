"""Autenticação — registro, login, isolamento de sessão (Missão 2 Fases 7/12).

Cobre: hash bcrypt idêntico no seed e no login, credencial errada negada,
email duplicado negado, token carrega o dono correto (base do anti-IDOR).
"""

import pytest

from config.security import verify_token
from schemas.user_schema import UserCreate, UserLogin
from services.auth_services import AuthService
from utils.exceptions import EmailAlreadyExistsError, InvalidCredentialsError


def test_register_and_login_roundtrip(db, isolated_limiter):
    svc = AuthService(db)
    user = svc.register_user(
        UserCreate(name="Maria Silva", email="maria@ex.com", password="Segura123")
    )
    assert user.id is not None

    token = svc.authenticate_user(UserLogin(email="maria@ex.com", password="Segura123"))
    assert token.user_id == user.id
    assert token.email == "maria@ex.com"
    assert verify_token(token.access_token) == user.id


def test_login_wrong_password_denied(db, isolated_limiter):
    svc = AuthService(db)
    svc.register_user(UserCreate(name="Joao Souza", email="joao@ex.com", password="Segura123"))
    with pytest.raises(InvalidCredentialsError):
        svc.authenticate_user(UserLogin(email="joao@ex.com", password="Errada123"))


def test_login_unknown_email_denied(db, isolated_limiter):
    with pytest.raises(InvalidCredentialsError):
        AuthService(db).authenticate_user(
            UserLogin(email="fantasma@ex.com", password="Qualquer123")
        )


def test_register_duplicate_email_denied(db, isolated_limiter):
    svc = AuthService(db)
    svc.register_user(UserCreate(name="Ana Lima", email="ana@ex.com", password="Segura123"))
    with pytest.raises(EmailAlreadyExistsError):
        svc.register_user(UserCreate(name="Ana2 Lima", email="ana@ex.com", password="Segura123"))


def test_resolve_user_rejects_forged_and_expired(db, sample_user):
    from config.security import create_access_token
    from middleware.auth_context import resolve_user
    from utils.exceptions import AuthenticationError

    good = {"token": create_access_token({"sub": str(sample_user.id)})}
    assert resolve_user(good) == sample_user.id
    # Mismatch: token de A com alegação de B.
    with pytest.raises(AuthenticationError):
        resolve_user(good, claimed_user_id=sample_user.id + 999)
    # Ausente / lixo.
    with pytest.raises(AuthenticationError):
        resolve_user(None)
    with pytest.raises(AuthenticationError):
        resolve_user({"token": "invalido"})
    with pytest.raises(AuthenticationError):
        resolve_user({})
