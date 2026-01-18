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

# ===============================
# LAYOUT PRINCIPAL
# ===============================
app.layout = html.Div([
    # URL para roteamento
    dcc.Location(id="url", refresh=False),
    
    # Stores globais
    dcc.Store(id="auth-store", storage_type="session"),
    dcc.Store(id="store-user-id", storage_type="session"),
    dcc.Store(id="store-reload-dashboard", storage_type="memory"),
    dcc.Store(id="store-modal-state", storage_type="memory", data={"is_open": False}),  # ← NOVO
    
    # Download components
    dcc.Download(id="download-extrato"),
    dcc.Download(id="download-dashboard"),
    
    # Modal de novo lançamento
    modal_novo_lancamento,
    
    # Conteúdo renderizado
    html.Div(id="page-content"),
])

# ===============================
# CALLBACK DE ROTEAMENTO
# ===============================
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
    Input("auth-store", "data"),
)
def display_page(pathname, auth_data):
    """
    Gerencia roteamento e controle de acesso.
    
    Args:
        pathname: Caminho da URL
        auth_data: Dados de autenticação
        
    Returns:
        Layout da página
    """
    # Páginas públicas (sem autenticação)
    public_pages = ["/", "/login", "/register"]
    
    # Se não autenticado e tentando acessar página privada
    if pathname not in public_pages and not auth_data:
        app_logger.warning(f"Acesso não autorizado: {pathname}")
        return login_page.layout
    
    # Roteamento
    if pathname == "/" or pathname == "/login":
        return login_page.layout
    
    elif pathname == "/register":
        return login_page.register_layout
    
    elif pathname == "/dashboard":
        if not auth_data:
            return login_page.layout
        return html.Div([
            sidebar,
            html.Div(
                dashboard_page.layout,
                className="content",
                style={"marginLeft": "280px", "padding": "20px"},
            )
        ])
    
    elif pathname == "/extrato":
        if not auth_data:
            return login_page.layout
        return html.Div([
            sidebar,
            html.Div(
                extrato_page.layout,
                className="content",
                style={"marginLeft": "280px", "padding": "20px"},
            )
        ])
    
    elif pathname == "/relatorios":
        if not auth_data:
            return login_page.layout
        return html.Div([
            sidebar,
            html.Div(
                relatorios_page.layout,
                className="content",
                style={"marginLeft": "280px", "padding": "20px"},
            )
        ])
    
    elif pathname == "/configuracoes":
        if not auth_data:
            return login_page.layout
        return html.Div([
            sidebar,
            html.Div(
                configuracoes_page.layout,
                className="content",
                style={"marginLeft": "280px", "padding": "20px"},
            )
        ])
    
    else:
        # Página 404
        from components.shared.error import error_page_404
        return error_page_404()

# ===============================
# REGISTRA CALLBACKS
# ===============================
# Deve vir depois da definição do layout
try:
    import callbacks
    app_logger.info("✅ Callbacks registrados com sucesso!")
except Exception as e:
    app_logger.error(f"❌ Erro ao registrar callbacks: {e}")
    import traceback
    traceback.print_exc()

# ===============================
# INICIALIZAÇÃO DO SERVIDOR
# ===============================
if __name__ == "__main__":
    from config.settings import settings
    
    app_logger.info(f"🚀 Iniciando servidor em http://localhost:{settings.PORT}")
    
    app.run_server(
        debug=settings.DEBUG,
        host=settings.HOST,
        port=settings.PORT,
        dev_tools_hot_reload=settings.DEBUG,
        dev_tools_ui=settings.DEBUG,
        dev_tools_serve_dev_bundles=settings.DEBUG,
    )
