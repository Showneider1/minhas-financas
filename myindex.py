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
    goals_page,
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
    # 1. Sinal principal — lido pelos callbacks de KPIs e gráficos
    dcc.Store(id="store-reload-dashboard", storage_type="memory"),

    # 2. Sinal auxiliar — escrito por confirmar_exclusao,
    #    propagado ao store-reload-dashboard pelo consolidador
    dcc.Store(id="store-reload-aux", storage_type="memory"),

    # 3. Guarda o ID da transação que está sendo editada
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
    public_pages = ["/", "/login", "/register"]

    if pathname not in public_pages and not auth_data:
        app_logger.warning(f"Acesso não autorizado: {pathname}")
        return login_page.layout

    if pathname in ("/", "/login"):
        return login_page.layout

    if pathname == "/register":
        return login_page.register_layout

    content = None

    if pathname == "/dashboard":
        content = dashboard_page.layout()

    elif pathname == "/extrato":
        content = extrato_page.layout

    elif pathname == "/relatorios":
        content = relatorios_page.layout

    elif pathname == "/configuracoes":
        content = configuracoes_page.layout

    elif pathname == "/metas":
        content = goals_page.layout

    else:
        try:
            from components.shared.error import error_page_404
            return error_page_404()
        except Exception:
            return html.Div(
                dbc.Container([
                    html.H1("404", className="display-1 fw-bold"),
                    html.P("Página não encontrada.", className="lead"),
                    dbc.Button("Voltar ao Início", href="/dashboard", color="primary"),
                ], className="py-5 text-center")
            )

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
