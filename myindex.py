"""
Arquivo principal - Entry point da aplicação.
Gerencia roteamento e layout principal.
"""
from dash import dcc, html, Input, Output
import dash_bootstrap_components as dbc
from app import app, server
from components.sidebar import sidebar, modal_novo_lancamento
from pages import (
    dashboard_page,
    extrato_page,
    relatorios_page,
    configuracoes_page,
    login_page,
)
from config.logging_config import app_logger
from middleware.auth_middleware import check_auth

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
app.layout = html.Div([
    # URL para roteamento
    dcc.Location(id="url", refresh=False),
    
    # Stores globais
    dcc.Store(id="auth-store", storage_type="session"),
    dcc.Store(id="store-user-id", storage_type="session"),
    dcc.Store(id="store-reload-dashboard", data=0),  # Centralizado na raiz
    
    # Download components
    dcc.Download(id="download-extrato"),
    dcc.Download(id="download-dashboard"),
    
    # Sidebar e Modal obrigatoriamente na raiz para o Dash compilar os Callbacks
    html.Div(sidebar, id="sidebar-container", style={"display": "none"}),
    modal_novo_lancamento,
    
    # Conteúdo renderizado
    html.Div(id="page-content"),
])


# ===============================
# CALLBACK DE ROTEAMENTO
# ===============================
@app.callback(
    [Output("page-content", "children"), Output("sidebar-container", "style")],
    [Input("url", "pathname"), Input("auth-store", "data")],
)
def display_page(pathname, auth_data):
    """
    Gerencia roteamento, visibilidade da Sidebar e validação de acesso.
    """
    public_pages = ["/", "/login", "/register"]
    is_authenticated = check_auth(auth_data)
    
    # Estilos de visibilidade da Sidebar
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
    
    # Roteamento
    if pathname == "/" or pathname == "/login":
        if is_authenticated:
            return dcc.Location(pathname="/dashboard", id="redirect-dash"), HIDE_SIDEBAR
        return render_layout(login_page.layout), HIDE_SIDEBAR
    
    elif pathname == "/register":
        if is_authenticated:
            return dcc.Location(pathname="/dashboard", id="redirect-dash"), HIDE_SIDEBAR
        return render_layout(login_page.register_layout), HIDE_SIDEBAR
    
    elif pathname == "/dashboard":
        if not is_authenticated:
            return render_layout(login_page.layout), HIDE_SIDEBAR
        return wrap_private(dashboard_page.layout), SHOW_SIDEBAR
    
    elif pathname == "/extrato":
        if not is_authenticated:
            return render_layout(login_page.layout), HIDE_SIDEBAR
        return wrap_private(extrato_page.layout), SHOW_SIDEBAR
    
    elif pathname == "/relatorios":
        if not is_authenticated:
            return render_layout(login_page.layout), HIDE_SIDEBAR
        return wrap_private(relatorios_page.layout), SHOW_SIDEBAR
    
    elif pathname == "/configuracoes":
        if not is_authenticated:
            return render_layout(login_page.layout), HIDE_SIDEBAR
        return wrap_private(configuracoes_page.layout), SHOW_SIDEBAR
    
    else:
        from components.shared.error import error_page_404
        return render_layout(error_page_404), HIDE_SIDEBAR


# ===============================
# REGISTRA CALLBACKS
# ===============================
try:
    import callbacks
    app_logger.info("Callbacks registrados")
except Exception as e:
    app_logger.warning(f"Erro ao registrar callbacks: {e}")


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
        dev_tools_ui=settings.DEBUG,
        dev_tools_serve_dev_bundles=settings.DEBUG,
    )
