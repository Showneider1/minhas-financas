"""
Entry point WSGI para Gunicorn.

Executa a inicialização idempotente (create_all + seeds) e expõe o servidor
Flask subjacente ao Dash.
"""

from app import initialize_application
from myindex import server

__all__ = ["server"]

initialize_application()
