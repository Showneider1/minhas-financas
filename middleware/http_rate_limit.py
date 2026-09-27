"""Rate limit HTTP para o servidor Dash/Flask (P1 segurança).

`init_http_rate_limit(server)` instala um `before_request` que limita o
endpoint `/_dash-update-component` (superfície de escrita da UI) por IP,
devolvendo HTTP 429 + `Retry-After` reais em rajada. Demais rotas passam
livremente. Desligável via `RATE_LIMIT_HTTP_ENABLED`.
"""

from flask import jsonify, request

from config.settings import settings
from middleware.rate_limiter import client_ip, hit

TARGET_ENDPOINT = "/_dash-update-component"


def init_http_rate_limit(server) -> None:
    """Anexa o hook ao Flask server (idempotente por atributo)."""
    if getattr(server, "_http_rate_limit_installed", False):
        return

    @server.before_request
    def _dash_rate_limit():
        if not settings.RATE_LIMIT_HTTP_ENABLED:
            return None
        if (request.path or "") != TARGET_ENDPOINT:
            return None
        allowed, retry = hit(
            "http",
            f"ip:{client_ip()}",
            settings.RATE_LIMIT_HTTP_PER_MINUTE,
            60,
        )
        if allowed:
            return None
        resp = jsonify(
            {
                "error": "rate_limited",
                "message": "Muitas requisições. Aguarde antes de tentar novamente.",
            }
        )
        resp.status_code = 429
        resp.headers["Retry-After"] = str(retry)
        return resp

    server._http_rate_limit_installed = True
