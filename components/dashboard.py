from dash import html, dcc
from datetime import date
import dash_bootstrap_components as dbc

# ===================
# DASHBOARD LAYOUT
# ===================

layout = dbc.Container(
    [
        # ======================================================
        # HERO / HEADER
        # ======================================================
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H2(
                            "Dashboard Financeiro",
                            className="display-6 fw-bold text-dark mb-1",
                        ),
                        html.P(
                            f"Visão geral atualizada • {date.today().strftime('%d/%m/%Y')}",
                            className="text-muted mb-0 small",
                        ),
                    ],
                    width="auto",
                ),
                dbc.Col(
                    dbc.Button(
                        [
                            html.I(className="bi bi-download me-2"),
                            "Exportar Relatório",
                        ],
                        id="btn-export-dashboard",
                        color="primary",
                        outline=True,
                        size="sm",
                        className="rounded-pill",
                    ),
                    width="auto",
                    className="ms-auto d-flex align-items-center",
                ),
            ],
            className="mb-4 align-items-center",
        ),

        # ======================================================
        # KPI CARDS
        # ======================================================
        dbc.Row(
            [
                # SALDO
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Div(
                                    [
                                        html.I(
                                            className="bi bi-wallet2 me-2 text-warning"
                                        ),
                                        html.Span(
                                            "Saldo Atual",
                                            className="text-muted small fw-bold text-uppercase",
                                        ),
                                    ],
                                    className="mb-2",
                                ),
                                html.H3(
                                    "—",
                                    id="kpi-saldo",
                                    className="fw-bold text-dark mb-1",
                                ),
                                html.Small(
                                    id="kpi-saldo-variacao",
                                    className="text-muted",
                                ),
                            ]
                        ),
                        className="shadow-sm border-0 h-100",
                        style={"borderLeft": "4px solid #FFC107"},
                    ),
                    md=4,
                    className="mb-4",
                ),

                # RECEITA
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Div(
                                    [
                                        html.I(
                                            className="bi bi-arrow-up-circle me-2 text-success"
                                        ),
                                        html.Span(
                                            "Receitas",
                                            className="text-muted small fw-bold text-uppercase",
                                        ),
                                    ],
                                    className="mb-2",
                                ),
                                html.H3(
                                    "—",
                                    id="kpi-receita",
                                    className="fw-bold text-success mb-1",
                                ),
                                html.Small(
                                    id="kpi-receita-variacao",
                                    className="text-muted",
                                ),
                            ]
                        ),
                        className="shadow-sm border-0 h-100",
                        style={"borderLeft": "4px solid #10B981"},
                    ),
                    md=4,
                    className="mb-4",
                ),

                # DESPESA
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.Div(
                                    [
                                        html.I(
                                            className="bi bi-arrow-down-circle me-2 text-danger"
                                        ),
                                        html.Span(
                                            "Despesas",
                                            className="text-muted small fw-bold text-uppercase",
                                        ),
                                    ],
                                    className="mb-2",
                                ),
                                html.H3(
                                    "—",
                                    id="kpi-despesa",
                                    className="fw-bold text-danger mb-1",
                                ),
                                html.Small(
                                    id="kpi-despesa-variacao",
                                    className="text-muted",
                                ),
                            ]
                        ),
                        className="shadow-sm border-0 h-100",
                        style={"borderLeft": "4px solid #EF4444"},
                    ),
                    md=4,
                    className="mb-4",
                ),
            ]
        ),

        # ======================================================
        # FILTROS (Accordion)
        # ======================================================
        dbc.Accordion(
            [
                dbc.AccordionItem(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Label(
                                            "Período",
                                            className="small fw-bold text-muted",
                                        ),
                                        dcc.DatePickerRange(
                                            id="dashboard-periodo",
                                            start_date=date.today().replace(day=1),
                                            end_date=date.today(),
                                            display_format="DD/MM/YYYY",
                                            className="w-100",
                                        ),
                                    ],
                                    md=4,
                                    className="mb-3",
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label(
                                            "Tipo",
                                            className="small fw-bold text-muted",
                                        ),
                                        dcc.Dropdown(
                                            id="dashboard-tipo",
                                            options=[
                                                {
                                                    "label": "📈 Receita",
                                                    "value": "receita",
                                                },
                                                {
                                                    "label": "📉 Despesa",
                                                    "value": "despesa",
                                                },
                                            ],
                                            multi=True,
                                            placeholder="Todos",
                                        ),
                                    ],
                                    md=4,
                                    className="mb-3",
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label(
                                            "Status",
                                            className="small fw-bold text-muted",
                                        ),
                                        dcc.Dropdown(
                                            id="dashboard-status",
                                            options=[
                                                {
                                                    "label": "Pago",
                                                    "value": "pago",
                                                },
                                                {
                                                    "label": "Recebido",
                                                    "value": "recebido",
                                                },
                                                {
                                                    "label": "Pendente",
                                                    "value": "pendente",
                                                },
                                            ],
                                            multi=True,
                                            placeholder="Todos",
                                        ),
                                    ],
                                    md=4,
                                    className="mb-3",
                                ),
                            ]
                        ),
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Label(
                                            "Categorias",
                                            className="small fw-bold text-muted",
                                        ),
                                        dcc.Dropdown(
                                            id="dashboard-categorias",
                                            options=[],
                                            multi=True,
                                            placeholder="Todas",
                                            persistence=True,
                                            persistence_type="session",
                                        ),
                                    ],
                                    md=6,
                                    className="mb-3",
                                ),
                                dbc.Col(
                                    dbc.Button(
                                        [
                                            html.I(
                                                className="bi bi-arrow-clockwise me-2"
                                            ),
                                            "Limpar Filtros",
                                        ],
                                        id="dashboard-limpar-filtros",
                                        color="light",
                                        className="w-100 border",
                                        size="sm",
                                    ),
                                    md=3,
                                    className="d-flex align-items-end",
                                ),
                            ]
                        ),
                    ],
                    title="🔍 Filtros Avançados",
                )
            ],
            start_collapsed=True,
            flush=True,
            className="mb-4 shadow-sm",
        ),

        # ======================================================
        # GRÁFICOS
        # ======================================================
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                html.H5(
                                    [
                                        html.I(
                                            className="bi bi-graph-up me-2"
                                        ),
                                        "Fluxo de Caixa",
                                    ],
                                    className="mb-0 fw-bold fs-6",
                                ),
                                className="bg-white border-0",
                            ),
                            dbc.CardBody(
                                dcc.Graph(
                                    id="grafico-fluxo-caixa",
                                    config={"displayModeBar": False},
                                    style={"height": "350px"},
                                ),
                                className="p-2",
                            ),
                        ],
                        className="shadow-sm border-0 h-100",
                    ),
                    md=8,
                    className="mb-4",
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                html.H5(
                                    [
                                        html.I(
                                            className="bi bi-pie-chart me-2"
                                        ),
                                        "Categorias",
                                    ],
                                    className="mb-0 fw-bold fs-6",
                                ),
                                className="bg-white border-0",
                            ),
                            dbc.CardBody(
                                dcc.Graph(
                                    id="grafico-categorias",
                                    config={"displayModeBar": False},
                                    style={"height": "350px"},
                                ),
                                className="p-2",
                            ),
                        ],
                        className="shadow-sm border-0 h-100",
                    ),
                    md=4,
                    className="mb-4",
                ),
            ]
        ),
    ],
    fluid=True,
    className="py-3",
)
