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
# HELPER DE LAYOUT (BUGFIX)
# ===============================
def render_layout(layout_obj):
    """
    Avalia o layout importado. Se for uma função (útil para layouts dinâmicos 
    que atualizam datas no Dash), ele invoca a função. 
    Caso contrário, retorna o componente diretamente.
    """
    if callable(layout_obj):
        return layout_obj()
    return layout_obj

# ===============================
# LAYOUT PRINCIPAL
# ===============================
app.layout = html.Div([
    # URL para roteamento
    dcc.Location(id="url", refresh=False),
    
    # Stores globais
    dcc.Store(id="auth-store", storage_type="session"),
    dcc.Store(id="store-user-id", storage_type="session"),
    
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
    Gerencia roteamento e controle de acesso com validação criptográfica.
    """
    # Páginas públicas (sem autenticação)
    public_pages = ["/", "/login", "/register"]
    
    # Validação do Token no Backend (Restauração de Segurança)
    is_authenticated = check_auth(auth_data)
    
    # Se não autenticado e tentando acessar página privada
    if pathname not in public_pages and not is_authenticated:
        app_logger.warning(f"Acesso não autorizado bloqueado: {pathname}")
        return render_layout(login_page.layout)
    
    # Roteamento
    if pathname == "/" or pathname == "/login":
        if is_authenticated:
            return dcc.Location(pathname="/dashboard", id="redirect-dashboard")
        return render_layout(login_page.layout)
    
    elif pathname == "/register":
        if is_authenticated:
            return dcc.Location(pathname="/dashboard", id="redirect-dashboard")
        return render_layout(login_page.register_layout)
    
    elif pathname == "/dashboard":
        if not is_authenticated:
            return render_layout(login_page.layout)
        return html.Div([
            sidebar,
            html.Div(
                render_layout(dashboard_page.layout),  # Proteção contra func layout
                className="content",
                style={"marginLeft": "280px", "padding": "20px"},
            )
        ])
    
    elif pathname == "/extrato":
        if not is_authenticated:
            return render_layout(login_page.layout)
        return html.Div([
            sidebar,
            html.Div(
                render_layout(extrato_page.layout),    # Proteção contra func layout
                className="content",
                style={"marginLeft": "280px", "padding": "20px"},
            )
        ])
    
    elif pathname == "/relatorios":
        if not is_authenticated:
            return render_layout(login_page.layout)
        return html.Div([
            sidebar,
            html.Div(
                render_layout(relatorios_page.layout), # Proteção contra func layout
                className="content",
                style={"marginLeft": "280px", "padding": "20px"},
            )
        ])
    
    elif pathname == "/configuracoes":
        if not is_authenticated:
            return render_layout(login_page.layout)
        return html.Div([
            sidebar,
            html.Div(
                render_layout(configuracoes_page.layout), # Proteção contra func layout
                className="content",
                style={"marginLeft": "280px", "padding": "20px"},
            )
        ])
    
    else:
        # Página 404
        from components.shared.error import error_page_404
        return render_layout(error_page_404)


# ===============================
# REGISTRA CALLBACKS
# ===============================
# Deve vir depois da definição do layout
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
