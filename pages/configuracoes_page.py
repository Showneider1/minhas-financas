"""
Página de configurações moderna - Categorias, Contas e Cartões.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc

# Cores pré-definidas para escolha do usuário
COLORS = [
    {"label": "🟢 Verde", "value": "#2ecc71"},
    {"label": "🔵 Azul", "value": "#3498db"},
    {"label": "🔴 Vermelho", "value": "#e74c3c"},
    {"label": "🟡 Amarelo", "value": "#f1c40f"},
    {"label": "🟣 Roxo", "value": "#9b59b6"},
    {"label": "⚫ Cinza", "value": "#95a5a6"},
    {"label": "🟠 Laranja", "value": "#e67e22"},
]

def render_empty_state(message, icon="bi-inbox"):
    return html.Div([
        html.I(className=f"bi {icon} display-4 text-muted mb-3"),
        html.H5(message, className="text-muted")
    ], className="text-center py-5")

layout = dbc.Container([
    # Header com estilo mais limpo
    dbc.Row([
        dbc.Col([
            html.H2("Minhas Configurações", className="fw-bold text-primary"),
            html.P("Gerencie suas contas, cartões e categorias de transação.", className="text-muted"),
        ]),
    ], className="mb-4 mt-4"),
    
    # Navegação em Abas (Estilo Card)
    dbc.Card([
        dbc.CardHeader(
            dbc.Tabs([
                dbc.Tab(label="📁 Categorias", tab_id="tab-categorias", label_class_name="fw-bold"),
                dbc.Tab(label="🏦 Contas Bancárias", tab_id="tab-contas", label_class_name="fw-bold"),
                dbc.Tab(label="💳 Cartões de Crédito", tab_id="tab-cartoes", label_class_name="fw-bold"),
            ], 
            id="tabs-configuracoes", 
            active_tab="tab-categorias",
            className="card-header-tabs"  # CORREÇÃO: Usar classe CSS em vez de card=True
            )
        ),
        dbc.CardBody([
            # Conteúdo dinâmico das abas
            html.Div(id="content-configuracoes"),
        ])
    ], className="shadow-sm border-0"),
    
    # Stores auxiliares
    dcc.Store(id="trigger-update-config", data=0), # Para forçar atualização
    
    # =========================================================
    # MODAIS (Janelas Flutuantes)
    # =========================================================
    
    # --- MODAL CATEGORIA ---
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Nova Categoria")),
        dbc.ModalBody([
            dbc.Label("Nome da Categoria"),
            dbc.Input(id="cat-nome", placeholder="Ex: Mercado, Salário...", className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Label("Tipo"),
                    dbc.Select(
                        id="cat-tipo",
                        options=[
                            {"label": "📉 Despesa", "value": "EXPENSE"},
                            {"label": "📈 Receita", "value": "INCOME"},
                        ],
                        value="EXPENSE",
                    )
                ], width=6),
                dbc.Col([
                    dbc.Label("Cor"),
                    dbc.Select(id="cat-cor", options=COLORS, value="#3498db")
                ], width=6),
            ], className="mb-3"),
            
            dbc.Label("Categoria Principal (Opcional)"),
            dbc.Select(id="cat-parent", options=[], placeholder="Selecione..."),
            html.Small("Selecione apenas se for criar uma subcategoria.", className="text-muted"),
        ]),
        dbc.ModalFooter([
            dbc.Button("Salvar Categoria", id="btn-save-cat", color="primary"),
        ]),
    ], id="modal-categoria", is_open=False),
    
    # --- MODAL CONTA BANCÁRIA ---
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Nova Conta Bancária")),
        dbc.ModalBody([
            dbc.Label("Nome da Conta"),
            dbc.Input(id="acc-nome", placeholder="Ex: Nubank, Carteira...", className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Label("Tipo"),
                    dbc.Select(
                        id="acc-tipo",
                        options=[
                            {"label": "Conta Corrente", "value": "CHECKING"},
                            {"label": "Poupança", "value": "SAVINGS"},
                            {"label": "Dinheiro", "value": "CASH"},
                            {"label": "Investimento", "value": "INVESTMENT"},
                        ],
                        value="CHECKING"
                    )
                ], width=6),
                dbc.Col([
                    dbc.Label("Saldo Atual"),
                    dbc.Input(id="acc-saldo", type="number", value=0, step=0.01)
                ], width=6),
            ], className="mb-3"),
        ]),
        dbc.ModalFooter([
            dbc.Button("Salvar Conta", id="btn-save-acc", color="success"),
        ]),
    ], id="modal-conta", is_open=False),
    
    # --- MODAL CARTÃO DE CRÉDITO ---
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Novo Cartão de Crédito")),
        dbc.ModalBody([
            dbc.Label("Apelido do Cartão"),
            dbc.Input(id="card-nome", placeholder="Ex: Nubank Platinum", className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Label("Limite Total (R$)"),
                    dbc.Input(id="card-limite", type="number", value=0, min=0)
                ], width=12),
            ], className="mb-3"),
            
            dbc.Row([
                dbc.Col([
                    dbc.Label("Dia Fechamento"),
                    dbc.Select(
                        id="card-fechamento",
                        options=[{"label": str(i), "value": i} for i in range(1, 32)],
                        value=1
                    )
                ], width=6),
                dbc.Col([
                    dbc.Label("Dia Vencimento"),
                    dbc.Select(
                        id="card-vencimento",
                        options=[{"label": str(i), "value": i} for i in range(1, 32)],
                        value=10
                    )
                ], width=6),
            ]),
        ]),
        dbc.ModalFooter([
            dbc.Button("Salvar Cartão", id="btn-save-card", color="warning"), # Warning para diferenciar visualmente
        ]),
    ], id="modal-cartao", is_open=False),

    # Toast de Feedback
    html.Div(id="config-feedback"),

], fluid=True, className="bg-light min-vh-100")