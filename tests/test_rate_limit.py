"""Rate limiting por IP + HTTP 429 (Missão P1 Fase 2/4).

- Buckets isolados por (scope, key); rajada bloqueia com retry_after.
- Login/register via AuthService com IP: bloqueio após o limite.
- Hook HTTP real: rajada no /_dash-update-component → 429 + Retry-After.
"""
import pytest

from config.settings import settings
from middleware.rate_limiter import hit
from schemas.user_schema import UserCreate, UserLogin
from services.auth_services import AuthService
from utils.exceptions import AuthenticationError


def test_bucket_allows_then_blocks(mem_factory):
    for _ in range(3):
        allowed, _ = hit("t", "k1", 3, 60, _session_factory=mem_factory)
        assert allowed is True
    allowed, retry = hit("t", "k1", 3, 60, _session_factory=mem_factory)
    assert allowed is False
    assert retry >= 0


def test_buckets_isolated_by_key(mem_factory):
    for _ in range(5):
        hit("t", "victim", 3, 60, _session_factory=mem_factory)
    allowed, _ = hit("t", "other", 3, 60, _session_factory=mem_factory)
    assert allowed is True


def test_login_ip_bucket_blocks_burst(db, isolated_limiter, monkeypatch):
    """Rajadas de login do mesmo IP bloqueiam (mesmo com emails variados)."""
    monkeypatch.setattr(settings, "RATE_LIMIT_LOGIN_PER_IP", 3)
    svc = AuthService(db)
    ip = "198.51.100.7"
    for i in range(3):
        with pytest.raises(Exception):
            svc.authenticate_user(
                UserLogin(email=f"nope{i}@ex.com", password="Errada123"),
                client_ip=ip)
    with pytest.raises(AuthenticationError) as exc:
        svc.authenticate_user(
            UserLogin(email="nope9@ex.com", password="Errada123"), client_ip=ip)
    assert exc.value.code == "RATE_LIMIT_LOGIN_IP"
    # Outro IP segue livre.
    with pytest.raises(Exception) as exc2:
        svc.authenticate_user(
            UserLogin(email="nope9@ex.com", password="Errada123"),
            client_ip="203.0.113.9")
    assert exc2.value.code != "RATE_LIMIT_LOGIN_IP"


def test_register_ip_bucket_blocks_mass_creation(
    db, sample_user, isolated_limiter, monkeypatch
):
    monkeypatch.setattr(settings, "RATE_LIMIT_REGISTER_PER_HOUR", 2)
    svc = AuthService(db)
    ip = "198.51.100.8"
    svc.register_user(UserCreate(name="Um Silva", email="um-r1@ex.com",
                                 password="Segura123"), client_ip=ip)
    svc.register_user(UserCreate(name="Dois Souza", email="dois-r1@ex.com",
                                 password="Segura123"), client_ip=ip)
    with pytest.raises(AuthenticationError) as exc:
        svc.register_user(UserCreate(name="Tres Lima", email="tres-r1@ex.com",
                                     password="Segura123"), client_ip=ip)
    assert exc.value.code == "RATE_LIMIT_REGISTER"


def test_http_hook_returns_429_on_burst(db_engine, isolated_limiter, monkeypatch):
    """ Rajada real no endpoint Dash → HTTP 429 + Retry-After. """
    import myindex  # noqa: F401 — registra app/callbacks

    from app import server

    monkeypatch.setattr(settings, "RATE_LIMIT_HTTP_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_HTTP_PER_MINUTE", 3)
    client = server.test_client()
    codes = []
    retry_after = None
    for _ in range(5):
        resp = client.post(
            "/_dash-update-component",
            json={},
            environ_base={"REMOTE_ADDR": "198.51.100.99"},
        )
        codes.append(resp.status_code)
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
    assert 429 in codes, f"esperado 429 na rajada, obtido {codes}"
    assert retry_after is not None
