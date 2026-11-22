"""CSRF: o endpoint de escrita do Dash rejeita origens cross-site."""

from flask import Flask

from middleware.http_rate_limit import init_http_rate_limit

ENDPOINT = "/_dash-update-component"


def _client(_isolated_limiter):
    app = Flask(__name__)
    init_http_rate_limit(app)

    @app.route(ENDPOINT, methods=["POST"])
    def dash_update():
        return "ok"

    return app.test_client()


def test_csrf_rejects_foreign_origin(isolated_limiter):
    response = _client(isolated_limiter).post(
        ENDPOINT, headers={"Origin": "https://evil.example"}, json={}
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "csrf_rejected"


def test_csrf_rejects_foreign_referer(isolated_limiter):
    response = _client(isolated_limiter).post(
        ENDPOINT, headers={"Referer": "https://evil.example/pagina"}, json={}
    )

    assert response.status_code == 403


def test_csrf_accepts_same_origin(isolated_limiter):
    response = _client(isolated_limiter).post(
        ENDPOINT, headers={"Origin": "http://localhost"}, json={}
    )

    assert response.status_code == 200


def test_csrf_accepts_requests_without_origin_header(isolated_limiter):
    """Requisições sem Origin/Referer não são bloqueadas pelo CSRF."""
    response = _client(isolated_limiter).post(ENDPOINT, json={})

    assert response.status_code == 200
