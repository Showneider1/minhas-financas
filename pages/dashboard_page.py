"""
Página principal - Dashboard.
Layout v4: filtros Despesa/Receita nos gráficos de categoria.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc
from datetime import date


def _kpi_card(title, kpi_id, color_class, info_id=None, icon=""):
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.Span(icon, className="me-2 fs-5"),
                html.Span(title, className="text-muted small fw-semibold"),
            ], className="mb-2"),
            html.H4(id=kpi_id, children="R$ ...", className=f"fw-bold mb-1 {color_class}"),
            html.Small(id=info_id, children="", className="text-muted") if info_id else html.Div(),
        ])
    ], className="shadow-sm border-0 h-100")


def layout():
    return dbc.Container([

        # Header
        dbc.Row([
            dbc.Col([
                html.H2("Dashboard", className="mb-0 fw-bold"),
                html.P("Visão geral das suas finanças", className="text-muted mb-0"),
            ], width=True),
            dbc.Col([
                dcc.DatePickerRange(
                    id="dashboard-periodo",
                    display_format="DD/MM/YYYY",
                    start_date=date.today().replace(day=1),
                    end_date=date.today(),
                ),
            ], width="auto", className="d-flex align-items-center me-2"),
            dbc.Col([
                dbc.Button(
                    [html.I(className="bi bi-arrow-repeat me-1"), "Atualizar"],
                    id="btn-update-dashboard",
                    color="secondary", outline=True, size="sm",
                ),
            ], width="auto", className="d-flex align-items-center"),
        ], align="center", className="mb-4"),

        # Linha 1: 4 KPIs
        dbc.Row([
            dbc.Col(_kpi_card("Saldo em Caixa",      "kpi-saldo",     "text-primary",                        icon="🏦"), width=12, sm=6, lg=3, className="mb-3"),
            dbc.Col(_kpi_card("Receitas",             "kpi-receita",   "text-success",  "kpi-receita-info",   icon="📈"), width=12, sm=6, lg=3, className="mb-3"),
            dbc.Col(_kpi_card("Despesas",             "kpi-despesa",   "text-danger",   "kpi-despesa-info",   icon="📉"), width=12, sm=6, lg=3, className="mb-3"),
            dbc.Col(_kpi_card("Resultado do Período", "kpi-resultado", "text-secondary","kpi-resultado-info", icon="⚖️"), width=12, sm=6, lg=3, className="mb-3"),
        ]),

        # Linha 2: Card de Projeção de Fechamento
        dbc.Row([
            dbc.Col([
                dcc.Loading(html.Div(id="dashboard-card-projecao"), type="dot"),
            ], width=12, className="mb-3"),
        ]),

        # Linha 3: Fluxo de Caixa (lg=8) + Próximos Vencimentos (lg=4)
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="bi bi-bar-chart-line me-2"),
                        "Fluxo de Caixa Mensal",
                    ], className="bg-white fw-bold border-0 pb-0"),
                    dbc.CardBody([
                        dcc.Loading(
                            dcc.Graph(
                                id="grafico-fluxo-caixa",
                                config={"displayModeBar": False},
                                style={"height": "280px"},
                            ),
                        ),
                    ], className="pt-2"),
                ], className="shadow-sm border-0 h-100"),
            ], width=12, lg=8, className="mb-3"),

            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="bi bi-calendar-event me-2 text-warning"),
                        "Próximos Vencimentos",
                    ], className="bg-white fw-bold border-0 pb-0"),
                    dbc.CardBody([
                        dcc.Loading(
                            html.Div(
                                id="tabela-proximos-vencimentos",
                                style={"overflowY": "auto", "maxHeight": "200px"},
                            ),
                        ),
                        html.Hr(className="my-2"),
                        dbc.Row([
                            dbc.Col([
                                html.Div("A Receber", className="text-muted small"),
                                html.Div(id="totalizador-rec-pendente",
                                         className="text-success fw-bold small"),
                            ], width=4),
                            dbc.Col([
                                html.Div("A Pagar", className="text-muted small"),
                                html.Div(id="totalizador-desp-pendente",
                                         className="text-danger fw-bold small"),
                            ], width=4),
                            dbc.Col([
                                html.Div("Saldo Prev.", className="text-muted small"),
                                html.Div(id="totalizador-saldo-previsto",
                                         className="fw-bold small"),
                            ], width=4),
                        ], className="mt-2 text-center"),
                    ], className="pt-2"),
                ], className="shadow-sm border-0 h-100"),
            ], width=12, lg=4, className="mb-3"),
        ]),

        # Linha 4: Distribuição por Categoria (lg=5) + Top Categorias (lg=7)
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        dbc.Row([
                            dbc.Col([
                                html.I(className="bi bi-pie-chart me-2"),
                                "Distribuição por Categoria",
                            ], width=True, className="fw-bold"),
                            dbc.Col([
                                dbc.RadioItems(
                                    id="filtro-tipo-categoria",      # ← Input do callback
                                    options=[
                                        {"label": "Despesas", "value": "EXPENSE"},
                                        {"label": "Receitas", "value": "INCOME"},
                                    ],
                                    value="EXPENSE",
                                    inline=True,
                                    className="small",
                                    inputClassName="me-1",
                                    labelClassName="me-3",
                                ),
                            ], width="auto", className="d-flex align-items-center"),
                        ], align="center"),
                    ], className="bg-white border-0 pb-0"),
                    dbc.CardBody([
                        dcc.Loading(
                            dcc.Graph(
                                id="grafico-categorias",
                                config={"displayModeBar": False},
                                style={"height": "260px"},
                            ),
                        ),
                    ], className="pt-2"),
                ], className="shadow-sm border-0 h-100"),
            ], width=12, lg=5, className="mb-3"),

            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        dbc.Row([
                            dbc.Col([
                                html.I(className="bi bi-list-ol me-2"),
                                "Top Categorias",
                            ], width=True, className="fw-bold"),
                            dbc.Col([
                                dbc.RadioItems(
                                    id="filtro-tipo-top-categorias",  # ← Output do sincronizar_filtro_top
                                    options=[
                                        {"label": "Despesas", "value": "EXPENSE"},
                                        {"label": "Receitas", "value": "INCOME"},
                                    ],
                                    value="EXPENSE",
                                    inline=True,
                                    className="small",
                                    inputClassName="me-1",
                                    labelClassName="me-3",
                                ),
                            ], width="auto", className="d-flex align-items-center"),
                        ], align="center"),
                    ], className="bg-white border-0 pb-0"),
                    dbc.CardBody([
                        dcc.Loading(html.Div(id="tabela-top-categorias")),
                    ], className="pt-2"),
                ], className="shadow-sm border-0 h-100"),
            ], width=12, lg=7, className="mb-3"),
        ]),

    ], fluid=True, className="py-4 px-3")