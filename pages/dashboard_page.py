from dash import dcc, html
import dash_bootstrap_components as dbc
from datetime import date
from components.budget_modal import modal_budget as budget_modal

# ===============================
# LAYOUT DO DASHBOARD
# ===============================
layout = html.Div([
    #dcc.Store(id="store-reload-dashboard", storage_type="memory"),
    
    # 1. TOPO: Filtros e Botões de Ação
    dbc.Row([
        # Título e Saudação
        dbc.Col([
            html.H2("Dashboard", className="fw-bold"),
            html.P("Visão geral das suas finanças", className="text-muted"),
        ], md=6),
        
        # Filtros de Data e Botão de Metas
        dbc.Col([
            dbc.Stack([
                # Botão de Metas
                dbc.Button(
                    [html.I(className="bi bi-bullseye me-2"), "Definir Metas"], 
                    id="btn-open-budget", 
                    color="primary", 
                    outline=True,
                    className="me-2"
                ),
                
                # Date Picker
                dcc.DatePickerRange(
                    id="dashboard-periodo",
                    start_date=date.today().replace(day=1),
                    end_date=date.today(),
                    display_format="DD/MM/YYYY",
                    className="form-control d-inline-block",
                    style={"border": "none", "width": "300px"} # Ajuste CSS inline se necessário
                ),
            ], direction="horizontal", className="justify-content-end")
        ], md=6, className="d-flex align-items-center justify-content-end"),
    ], className="mb-4 align-items-end"),
    
    # 2. CARDS DE KPI (Resumo)
    dbc.Row([
        # Saldo
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Saldo Total", className="card-subtitle text-muted mb-2"),
                    html.H3(id="kpi-saldo", className="card-title fw-bold"),
                    html.Small(id="kpi-saldo-variacao", className="text-muted"),
                ])
            ], className="shadow-sm border-0 h-100")
        ], md=4, className="mb-3"),
        
        # Receitas
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Receitas", className="card-subtitle text-success mb-2"),
                    html.H3(id="kpi-receita", className="card-title fw-bold text-success"),
                    html.Small(id="kpi-receita-variacao", className="text-muted"),
                ])
            ], className="shadow-sm border-0 h-100")
        ], md=4, className="mb-3"),
        
        # Despesas
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Despesas", className="card-subtitle text-danger mb-2"),
                    html.H3(id="kpi-despesa", className="card-title fw-bold text-danger"),
                    html.Small(id="kpi-despesa-variacao", className="text-muted"),
                ])
            ], className="shadow-sm border-0 h-100")
        ], md=4, className="mb-3"),
    ]),
    
    # 3. SEÇÃO DE METAS (NOVO)
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="bi bi-bullseye me-2 text-primary"),
                    "Progresso das Metas (Mês Atual)"
                ], className="fw-bold bg-white"),
                dbc.CardBody(
                    id="container-budgets", # <--- O CALLBACK VAI INJETAR AS BARRAS AQUI
                    children=[
                        # Spinner enquanto carrega
                        dbc.Spinner(color="primary", size="sm")
                    ]
                )
            ], className="shadow-sm border-0 mb-4")
        ], md=12),
    ]),

    # 4. GRÁFICOS
    dbc.Row([
        # Gráfico Fluxo de Caixa
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Fluxo de Caixa", className="bg-white fw-bold"),
                dbc.CardBody([
                    dcc.Graph(id="grafico-fluxo-caixa", config={"displayModeBar": False})
                ])
            ], className="shadow-sm border-0 mb-4")
        ], md=8),
        
        # Gráfico Categorias
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Despesas por Categoria", className="bg-white fw-bold"),
                dbc.CardBody([
                    dcc.Graph(id="grafico-categorias", config={"displayModeBar": False})
                ])
            ], className="shadow-sm border-0 mb-4")
        ], md=4),
    ]),
    
    # MODAL DE METAS (Invisível até clicar)
    budget_modal
])