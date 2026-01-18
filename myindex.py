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
    
    # Stores globais (Memória do navegador)
    dcc.Store(id="auth-store", storage_type="session"),
    dcc.Store(id="store-user-id", storage_type="session"),
    
    # === SINAIS DE ATUALIZAÇÃO ===
    # 1. Avisa que o Dashboard/Extrato precisa recarregar
    dcc.Store(id="store-reload-dashboard", storage_type="memory"),
    
    # 2. Guarda o ID da transação que está sendo editada (Novo!)
    dcc.Store(id="store-transacao-id-editar", data=None, storage_type="memory"),
    # =============================

    dcc.Store(id="store-modal-state", storage_type="memory", data={"is_open": False}),
    
    # Download components
    dcc.Download(id="download-extrato"),
    dcc.Download(id="download-dashboard"),
    
    # Modal de novo lançamento (Global)
    modal_novo_lancamento,
    
    # Conteúdo renderizado (Páginas)
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
    
    # --- ÁREA RESTRITA (COM SIDEBAR) ---
    content = None
    
    if pathname == "/dashboard":
        content = dashboard_page.layout
    
    elif pathname == "/extrato":
        content = extrato_page.layout
    
    elif pathname == "/relatorios":
        content = relatorios_page.layout
    
    elif pathname == "/configuracoes":
        content = configuracoes_page.layout
    
    else:
        # Página 404
        try:
            from components.shared.error import error_page_404
            return error_page_404()
        except:
            return html.Div(
                dbc.Container(
                    [
                        html.H1("404", className="display-1 fw-bold"),
                        html.P("Página não encontrada.", className="lead"),
                        dbc.Button("Voltar ao Início", href="/dashboard", color="primary"),
                    ],
                    className="py-5 text-center"
                )
            )

    # Se a página foi encontrada e usuário está logado, retorna com Sidebar
    if content:
        return html.Div([
            sidebar,
            html.Div(
                content,
                className="content",
                style={"marginLeft": "280px", "padding": "20px"},
            )
        ])
    
    return login_page.layout

# ===============================
# REGISTRA CALLBACKS
# ===============================
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
    )