import dash_bootstrap_components as dbc
from dash import html, dcc
from datetime import date

# ==========================================
# LAYOUT DO DASHBOARD
# ==========================================
layout = dbc.Container(
    [
        # 1. TÍTULO E FILTROS
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H2("Dashboard", className="display-6 fw-bold"),
                        html.P("Visão geral das suas finanças", className="lead text-muted"),
                    ],
                    width=8,
                ),
                dbc.Col(
                    [
                        html.Label("Período de Análise:", className="fw-bold text-muted small"),
                        dcc.DatePickerRange(
                            id="dashboard-periodo",
                            start_date=date.today().replace(day=1), # Começa dia 1º
                            end_date=date.today(),
                            display_format="DD/MM/YYYY",
                            className="d-block mb-2",
                            style={"zIndex": 100} # Correção visual para não ficar atrás de cards
                        ),
                    ],
                    width=4,
                    className="text-end",
                ),
            ],
            className="mb-4 align-items-end",
        ),

        # 2. CARDS DE KPI (SALDO, RECEITA, DESPESA)
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("Saldo Total", className="card-subtitle mb-2 text-muted"),
                                html.H3("R$ 0,00", id="kpi-saldo", className="card-title text-primary fw-bold"),
                            ]
                        ),
                        className="shadow-sm border-0 h-100",
                    ),
                    width=4,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("Receitas (Realizadas)", className="card-subtitle mb-2 text-muted"),
                                html.H3("R$ 0,00", id="kpi-receita", className="card-title text-success fw-bold"),
                            ]
                        ),
                        className="shadow-sm border-0 h-100",
                    ),
                    width=4,
                ),
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("Despesas (Pagas)", className="card-subtitle mb-2 text-muted"),
                                html.H3("R$ 0,00", id="kpi-despesa", className="card-title text-danger fw-bold"),
                            ]
                        ),
                        className="shadow-sm border-0 h-100",
                    ),
                    width=4,
                ),
            ],
            className="mb-4",
        ),

        # 3. GRÁFICOS PRINCIPAIS
        dbc.Row(
            [
                # Gráfico de Fluxo de Caixa
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H5("Fluxo de Caixa", className="card-title mb-4"),
                                dcc.Graph(id="grafico-fluxo-caixa", config={"displayModeBar": False}),
                            ]
                        ),
                        className="shadow-sm border-0",
                    ),
                    width=8,
                ),
                
                # Painel de Metas (Budget) - ONDE ESTAVA O ERRO
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                dbc.Row([
                                    dbc.Col(html.H5("Metas do Mês", className="card-title")),
                                    dbc.Col(
                                        dbc.Button(
                                            html.I(className="bi bi-plus-lg"),
                                            id="btn-open-budget",
                                            color="outline-primary",
                                            size="sm",
                                            className="rounded-circle"
                                        ),
                                        width="auto"
                                    )
                                ], className="mb-4 align-items-center"),
                                
                                # AQUI: O container que faltava e travava o callback!
                                html.Div(id="container-budgets", style={"maxHeight": "300px", "overflowY": "auto"}),
                            ]
                        ),
                        className="shadow-sm border-0 h-100",
                    ),
                    width=4,
                ),
            ],
            className="mb-4",
        ),
        
        # 4. GRÁFICO DE CATEGORIAS (LINHA DE BAIXO)
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H5("Despesas por Categoria", className="card-title mb-4"),
                                dcc.Graph(id="grafico-categorias", config={"displayModeBar": False}),
                            ]
                        ),
                        className="shadow-sm border-0",
                    ),
                    width=12,
                ),
            ],
             className="mb-5",
        ),

        # 5. MODAL DE DEFINIR META (Invisível até clicar)
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Definir Meta de Gastos")),
                dbc.ModalBody(
                    [
                        dbc.Label("Categoria"),
                        dbc.Select(id="select-budget-category", placeholder="Selecione..."),
                        html.Br(),
                        dbc.Label("Valor Limite (R$)"),
                        dbc.Input(id="input-budget-amount", type="number", placeholder="Ex: 500.00"),
                        html.Div(id="budget-feedback", className="mt-3"),
                    ]
                ),
                dbc.ModalFooter(
                    [
                        dbc.Button("Fechar", id="btn-close-budget", className="ms-auto", n_clicks=0),
                        dbc.Button("Salvar Meta", id="btn-save-budget", color="primary", n_clicks=0),
                    ]
                ),
            ],
            id="modal-budget",
            is_open=False,
        ),
    ],
    fluid=True,
    className="py-4",
)