"""
Página de Configurações — Categorias, Contas e Cartões.
Botões de adicionar ficam no layout estático para evitar
disparo automático de modais ao re-renderizar conteúdo dinâmico.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc

COLORS = [
    {"label": "🟢 Verde",     "value": "#2ecc71"},
    {"label": "🔵 Azul",      "value": "#3498db"},
    {"label": "🔴 Vermelho",  "value": "#e74c3c"},
    {"label": "🟡 Amarelo",   "value": "#f1c40f"},
    {"label": "🟣 Roxo",      "value": "#9b59b6"},
    {"label": "⚫ Cinza",     "value": "#95a5a6"},
    {"label": "🟠 Laranja",   "value": "#e67e22"},
    {"label": "🩷 Rosa",      "value": "#e91e8c"},
    {"label": "🩵 Ciano",     "value": "#00bcd4"},
]

# ─── Modais (estáticos — nunca recriados) ────────────────────────────────────

modal_categoria = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle([
        html.I(className="bi bi-tags-fill me-2 text-primary"),
        html.Span(id="modal-cat-title", children="Nova Categoria"),
    ]), close_button=True),
    dbc.ModalBody([
        dcc.Store(id="cat-edit-id", data=None),
        dbc.Row([
            dbc.Col([
                dbc.Label("Nome *", className="fw-bold"),
                dbc.Input(id="cat-nome", placeholder="Ex: Mercado, Salário...", maxLength=80),
            ]),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Tipo *", className="fw-bold"),
                dbc.Select(id="cat-tipo", options=[
                    {"label": "📉 Despesa", "value": "EXPENSE"},
                    {"label": "📈 Receita", "value": "INCOME"},
                ], value="EXPENSE"),
            ], width=6),
            dbc.Col([
                dbc.Label("Cor", className="fw-bold"),
                dbc.Select(id="cat-cor", options=COLORS, value="#3498db"),
            ], width=6),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Subcategoria de (opcional)", className="fw-bold"),
                dbc.Select(id="cat-parent", options=[], value="",
                           placeholder="Nenhuma — categoria principal"),
                html.Small("Deixe em branco para criar uma categoria principal.",
                           className="text-muted"),
            ]),
        ], className="mb-3"),
        html.Div(id="cat-modal-feedback"),
    ]),
    dbc.ModalFooter([
        dbc.Button([html.I(className="bi bi-x me-1"), "Cancelar"],
                   id="btn-cancel-cat", color="secondary", outline=True, n_clicks=0),
        dbc.Button([html.I(className="bi bi-check2 me-1"), "Salvar"],
                   id="btn-save-cat", color="primary", n_clicks=0),
    ]),
], id="modal-categoria", is_open=False, backdrop="static")

modal_conta = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle([
        html.I(className="bi bi-bank2 me-2 text-success"),
        "Nova Conta Bancária",
    ]), close_button=True),
    dbc.ModalBody([
        dbc.Row([
            dbc.Col([
                dbc.Label("Nome da Conta *", className="fw-bold"),
                dbc.Input(id="acc-nome", placeholder="Ex: Nubank, Carteira...", maxLength=80),
            ]),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Tipo *", className="fw-bold"),
                dbc.Select(id="acc-tipo", options=[
                    {"label": "🏦 Conta Corrente",  "value": "CHECKING"},
                    {"label": "🐷 Poupança",         "value": "SAVINGS"},
                    {"label": "💵 Dinheiro",         "value": "CASH"},
                    {"label": "📈 Investimento",     "value": "INVESTMENT"},
                ], value="CHECKING"),
            ], width=6),
            dbc.Col([
                dbc.Label("Saldo Inicial (R$)", className="fw-bold"),
                dbc.InputGroup([
                    dbc.InputGroupText("R$"),
                    dbc.Input(id="acc-saldo", type="number", value=0, step=0.01),
                ]),
            ], width=6),
        ], className="mb-3"),
        html.Div(id="acc-modal-feedback"),
    ]),
    dbc.ModalFooter([
        dbc.Button([html.I(className="bi bi-x me-1"), "Cancelar"],
                   id="btn-cancel-acc", color="secondary", outline=True, n_clicks=0),
        dbc.Button([html.I(className="bi bi-check2 me-1"), "Salvar"],
                   id="btn-save-acc", color="success", n_clicks=0),
    ]),
], id="modal-conta", is_open=False, backdrop="static")

modal_cartao = dbc.Modal([
    dbc.ModalHeader(dbc.ModalTitle([
        html.I(className="bi bi-credit-card-fill me-2 text-warning"),
        "Novo Cartão de Crédito",
    ]), close_button=True),
    dbc.ModalBody([
        dbc.Row([
            dbc.Col([
                dbc.Label("Apelido do Cartão *", className="fw-bold"),
                dbc.Input(id="card-nome", placeholder="Ex: Nubank Platinum", maxLength=80),
            ]),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Limite Total (R$)", className="fw-bold"),
                dbc.InputGroup([
                    dbc.InputGroupText("R$"),
                    dbc.Input(id="card-limite", type="number", value=0, min=0, step=0.01),
                ]),
            ], width=12),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Dia Fechamento", className="fw-bold"),
                dbc.Select(id="card-fechamento",
                           options=[{"label": str(i), "value": i} for i in range(1, 29)],
                           value=1),
            ], width=6),
            dbc.Col([
                dbc.Label("Dia Vencimento", className="fw-bold"),
                dbc.Select(id="card-vencimento",
                           options=[{"label": str(i), "value": i} for i in range(1, 29)],
                           value=10),
            ], width=6),
        ], className="mb-3"),
        html.Div(id="card-modal-feedback"),
    ]),
    dbc.ModalFooter([
        dbc.Button([html.I(className="bi bi-x me-1"), "Cancelar"],
                   id="btn-cancel-card", color="secondary", outline=True, n_clicks=0),
        dbc.Button([html.I(className="bi bi-check2 me-1"), "Salvar"],
                   id="btn-save-card", color="warning", n_clicks=0),
    ]),
], id="modal-cartao", is_open=False, backdrop="static")

# ─── Layout principal ─────────────────────────────────────────────────────────

layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H2([html.I(className="bi bi-gear-fill me-2 text-primary"), "Configurações"],
                    className="fw-bold mb-0"),
            html.P("Gerencie suas contas, cartões e categorias de transação.",
                   className="text-muted mb-0"),
        ], width=True),
        # Botões de adicionar — ESTÁTICOS, sempre presentes no DOM
        dbc.Col([
            # Cada botão só aparece na aba correspondente (controlado por callback)
            html.Div(id="config-action-buttons"),
        ], width="auto", className="d-flex align-items-center"),
    ], align="center", className="mb-4 mt-3"),

    dcc.Store(id="trigger-update-config", data=0),

    # Abas
    dbc.Card([
        dbc.CardHeader(
            dbc.Tabs([
                dbc.Tab(label="📁 Categorias",       tab_id="tab-categorias",
                        label_class_name="fw-semibold"),
                dbc.Tab(label="🏦 Contas Bancárias", tab_id="tab-contas",
                        label_class_name="fw-semibold"),
                dbc.Tab(label="💳 Cartões",          tab_id="tab-cartoes",
                        label_class_name="fw-semibold"),
            ], id="tabs-configuracoes", active_tab="tab-categorias",
               className="card-header-tabs"),
        ),
        dbc.CardBody(dcc.Loading(
            html.Div(id="content-configuracoes"),
            type="dot",
        )),
    ], className="shadow-sm border-0"),

    # Toast de feedback (posição fixa)
    html.Div(id="config-feedback"),

    # Modais estáticos
    modal_categoria,
    modal_conta,
    modal_cartao,

], fluid=True, className="py-4 px-3")
