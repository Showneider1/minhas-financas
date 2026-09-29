"""
Arquivo principal - Entry point da aplicação.
Gerencia roteamento e layout principal.
"""

from dash import Input, Output, dcc, html

import callbacks  # noqa: F401
from app import app, server
from components.sidebar import modal_novo_lancamento, sidebar
from config.logging_config import app_logger
from middleware.auth_middleware import check_auth
from middleware.http_rate_limit import init_http_rate_limit
from pages import (
    analytics_page,
    cartoes_page,
    configuracoes_page,
    dashboard_page,
    extrato_page,
    goals_page,
    importacao_page,
    investimentos_page,
    login_page,
    recorrencia_page,
    relatorios_page,
)

# P1 segurança: rajadas no endpoint de escrita retornam HTTP 429 por IP.
init_http_rate_limit(server)


# ===============================
# HELPERS DE LAYOUT
# ===============================
def render_layout(layout_obj):
    """Renderiza layout estático ou executa função de layout dinâmico."""
    if callable(layout_obj):
        return layout_obj()
    return layout_obj


# ===============================
# LAYOUT PRINCIPAL (BUGFIX DE RAIZ)
# ===============================
app.layout = html.Div(
    [
        # URL para roteamento
        dcc.Location(id="url", refresh=False),
        # Stores globais
        dcc.Store(id="auth-store", storage_type="session"),
        dcc.Store(id="store-user-id", storage_type="session"),
        dcc.Store(id="store-reload-dashboard", data=0),
        dcc.Store(id="store-reload-aux", storage_type="memory"),
        dcc.Store(id="store-transacao-id-editar", data=None, storage_type="memory"),
        dcc.Store(id="store-modal-state", storage_type="memory", data={"is_open": False}),
        # Download components
        dcc.Download(id="download-extrato"),
        dcc.Download(id="download-dashboard"),
        # Sidebar e Modal obrigatoriamente na raiz para o Dash compilar os Callbacks
        html.Div(sidebar, id="sidebar-container", style={"display": "none"}),
        modal_novo_lancamento,
        # Conteúdo renderizado
        html.Div(id="page-content"),
    ]
)


# ===============================
# CALLBACK DE ROTEAMENTO
# ===============================
@app.callback(
    [Output("page-content", "children"), Output("sidebar-container", "style")],
    [Input("url", "pathname"), Input("auth-store", "data")],
)
def display_page(pathname, auth_data):
    """Gerencia roteamento, visibilidade da Sidebar e validação de acesso."""
    public_pages = ["/", "/login", "/register"]
    is_authenticated = check_auth(auth_data)

    HIDE_SIDEBAR = {"display": "none"}
    SHOW_SIDEBAR = {"display": "block"}

    def wrap_private(layout_component):
        return html.Div(
            render_layout(layout_component),
            className="content",
            style={"marginLeft": "280px", "padding": "20px"},
        )

    # Bloqueio de acesso
    if pathname not in public_pages and not is_authenticated:
        app_logger.warning(f"Acesso não autorizado bloqueado: {pathname}")
        return render_layout(login_page.layout), HIDE_SIDEBAR

    if pathname in ("/", "/login"):
        if is_authenticated:
            return dcc.Location(pathname="/dashboard", id="redirect-dash"), HIDE_SIDEBAR
        return render_layout(login_page.layout), HIDE_SIDEBAR

    if pathname == "/register":
        if is_authenticated:
            return dcc.Location(pathname="/dashboard", id="redirect-dash"), HIDE_SIDEBAR
        return render_layout(login_page.register_layout), HIDE_SIDEBAR

    if pathname == "/dashboard":
        if not is_authenticated:
            return render_layout(login_page.layout), HIDE_SIDEBAR
        return wrap_private(dashboard_page.layout), SHOW_SIDEBAR

    if pathname == "/extrato":
        if not is_authenticated:
            return render_layout(login_page.layout), HIDE_SIDEBAR
        return wrap_private(extrato_page.layout), SHOW_SIDEBAR

    if pathname == "/relatorios":
        if not is_authenticated:
            return render_layout(login_page.layout), HIDE_SIDEBAR
        return wrap_private(relatorios_page.layout), SHOW_SIDEBAR

    if pathname == "/configuracoes":
        if not is_authenticated:
            return render_layout(login_page.layout), HIDE_SIDEBAR
        return wrap_private(configuracoes_page.layout), SHOW_SIDEBAR

    if pathname == "/metas":
        if not is_authenticated:
            return render_layout(login_page.layout), HIDE_SIDEBAR
        return wrap_private(goals_page.layout), SHOW_SIDEBAR

    if pathname == "/investimentos":
        if not is_authenticated:
            return render_layout(login_page.layout), HIDE_SIDEBAR
        return wrap_private(investimentos_page.layout), SHOW_SIDEBAR

    if pathname == "/cartoes":
        if not is_authenticated:
            return render_layout(login_page.layout), HIDE_SIDEBAR
        return wrap_private(cartoes_page.layout), SHOW_SIDEBAR

    if pathname == "/analytics":
        if not is_authenticated:
            return render_layout(login_page.layout), HIDE_SIDEBAR
        return wrap_private(analytics_page.layout), SHOW_SIDEBAR

    if pathname == "/importacao":
        if not is_authenticated:
            return render_layout(login_page.layout), HIDE_SIDEBAR
        return wrap_private(importacao_page.layout), SHOW_SIDEBAR

    if pathname == "/recorrencia":
        if not is_authenticated:
            return render_layout(login_page.layout), HIDE_SIDEBAR
        return wrap_private(recorrencia_page.layout), SHOW_SIDEBAR

    from components.shared.error import error_page_404

    return render_layout(error_page_404), HIDE_SIDEBAR


# ===============================
# INICIALIZAÇÃO DO SERVIDOR
# ===============================
if __name__ == "__main__":
    from config.settings import settings

    app_logger.info(f"Iniciando servidor em http://localhost:{settings.PORT}")

    app.run_server(
        debug=settings.DEBUG,
        host=settings.HOST,
        port=settings.PORT,
        dev_tools_hot_reload=settings.DEBUG,
    )
