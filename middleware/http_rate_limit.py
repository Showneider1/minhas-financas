"""Rate limit HTTP para o servidor Dash/Flask (P1 segurança).

`init_http_rate_limit(server)` instala um `before_request` que limita o
endpoint `/_dash-update-component` (superfície de escrita da UI) por IP,
devolvendo HTTP 429 + `Retry-After` reais em rajada. Demais rotas passam
livremente. Desligável via `RATE_LIMIT_HTTP_ENABLED`.
"""

from urllib.parse import urlparse

from flask import jsonify, request

from config.settings import settings
from middleware.rate_limiter import client_ip, hit

TARGET_ENDPOINT = "/_dash-update-component"


def _csrf_violation():
    """Bloqueia POST cross-site no endpoint de escrita do Dash.

    O Dash envia as requisições de callback via fetch same-origin; navegadores
    modernos incluem `Origin` (e geralmente `Referer`). Não exigimos header
    customizado porque o cliente Dash não o envia — isso quebraria a UI.
    """
    if request.method != "POST":
        return None
    host_name = (request.host or "").split(":")[0]

    def same_origin(value: str) -> bool:
        parsed = urlparse(value)
        return parsed.hostname == host_name

    origin = request.headers.get("Origin")
    referer = request.headers.get("Referer")
    if (origin and not same_origin(origin)) or (referer and not same_origin(referer)):
        resp = jsonify({"error": "csrf_rejected", "message": "Origem não autorizada."})
        resp.status_code = 403
        return resp
    return None


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
        violation = _csrf_violation()
        if violation is not None:
            return violation
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
