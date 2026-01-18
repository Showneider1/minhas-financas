"""
Aplicação principal com layout base e roteamento.
"""
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State
from app import app
from config.logging_config import app_logger

# Importa callbacks
from callbacks import (
    auth_callbacks,
    transactions_callbacks,
    dashboard_callbacks,
    extrato_callbacks,
    export_callbacks,
)

# Importa páginas
from pages import dashboard_page, extrato_page, login_page

# Importa componentes
from components.sidebar import create_sidebar
from components.transaction_modal import create_transaction_modal


# ====================
# LAYOUT PRINCIPAL
# ====================

app.layout = dbc.Container([
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="auth-store", storage_type="session"),
    dcc.Store(id="store-user-id", storage_type="session"),
    dcc.Store(id="store-reload-dashboard", data=0, storage_type="memory"),
    
    # Downloads
    dcc.Download(id="download-extrato"),
    dcc.Download(id="download-dashboard"),
    
    # Modal de transação - APENAS AQUI!
    create_transaction_modal(),
    
    # Conteúdo da página
    html.Div(id="page-content"),
    
], fluid=True, className="p-0")


# ====================
# CALLBACK DE ROTEAMENTO
# ====================

@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
    State("auth-store", "data"),
)
def display_page(pathname, auth_data):
    """
    Controla roteamento e autenticação.
    """
    try:
        print(f"\n🔀 ROTEAMENTO:")
        print(f"   pathname: {pathname}")
        print(f"   auth_data: {auth_data}")
        
        # Verifica autenticação
        is_authenticated = auth_data and auth_data.get("authenticated")
        print(f"   is_authenticated: {is_authenticated}")
        
        # Páginas públicas
        if pathname in ["/", "/login"]:
            print(f"   → Retornando login")
            return login_page.layout
        
        # Redireciona não autenticados
        if not is_authenticated:
            print(f"   → Redirecionando para login")
            return login_page.layout
        
        # Páginas autenticadas
        if pathname == "/dashboard":
            print(f"   → Retornando dashboard")
            return dbc.Row([
                dbc.Col(create_sidebar(), width=2, className="p-0"),
                dbc.Col(dashboard_page.layout, width=10, className="p-0"),
            ], className="g-0")
        
        elif pathname == "/extrato":
            print(f"   → Retornando extrato")
            return dbc.Row([
                dbc.Col(create_sidebar(), width=2, className="p-0"),
                dbc.Col(extrato_page.layout, width=10, className="p-0"),
            ], className="g-0")
        
        # 404
        print(f"   → 404")
        return dbc.Container([
            html.H1("404", className="text-center mt-5"),
            html.P("Página não encontrada", className="text-center"),
            dbc.Button("Voltar ao Login", href="/login", color="primary"),
        ])
    
    except Exception as e:
        print(f"\n❌ ERRO NO ROTEAMENTO:")
        print(f"   {e}")
        import traceback
        traceback.print_exc()
        
        return dbc.Container([
            dbc.Alert(
                f"Erro ao carregar página: {str(e)}",
                color="danger",
                className="mt-5"
            ),
            dbc.Button("Voltar ao Login", href="/login", color="primary"),
        ])


# ====================
# EXECUÇÃO
# ====================

if __name__ == "__main__":
    app_logger.info("🚀 Iniciando aplicação...")
    app.run(
        debug=True,
        host="0.0.0.0",
        port=8050,
    )
