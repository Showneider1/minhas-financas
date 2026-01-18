from dash import html, dcc
from dash.dependencies import Input, Output, State
from datetime import date
import dash_bootstrap_components as dbc
import locale
from app import app
from components.shared.cards import kpi_card

# =============================
# CONFIGURAÇÕES LOCALE
# =============================
try:
    locale.setlocale(locale.LC_TIME, "pt_BR.UTF-8")
except:
    pass

MES_ANO_ATUAL = date.today().strftime("%B %Y").capitalize()

# =============================
# LAYOUT — EXTRATO
# =============================
layout = dbc.Container(
    [
        # Header
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H2("Extrato Completo", className="display-6 fw-bold mb-1"),
                        html.P(
                            f"Histórico detalhado de transações • {MES_ANO_ATUAL}",
                            className="text-muted small mb-0",
                        ),
                    ]
                ),
                dbc.Col(
                    dbc.ButtonGroup(
                        [
                            dbc.Button(
                                [html.I(className="bi bi-file-earmark-pdf me-2"), "PDF"],
                                color="light", size="sm", className="border", id="btn-export-pdf",
                            ),
                            dbc.Button(
                                [html.I(className="bi bi-file-earmark-excel me-2"), "Excel"],
                                color="light", size="sm", className="border", id="btn-export-excel",
                            ),
                        ]
                    ),
                    width="auto",
                    className="ms-auto d-flex align-items-center",
                ),
            ],
            className="mb-4 align-items-center",
        ),

        # KPIs
        dbc.Row(
            [
                kpi_card("Total Entradas", "total-entradas-extrato", "8.200,00", "12 transações", "success"),
                kpi_card("Total Saídas", "total-saidas-extrato", "4.200,00", "8 transações", "danger"),
                kpi_card("Saldo Líquido", "saldo-periodo-extrato", "4.000,00", "Período selecionado", "primary"),
            ],
            className="mb-3",
        ),

        # Barra de Busca / Ordenação
        dbc.Card(
            dbc.CardBody(
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.InputGroup(
                                [
                                    dbc.InputGroupText(html.I(className="bi bi-search"), className="bg-light border-0"),
                                    dbc.Input(id="busca-extrato", placeholder="Buscar por descrição, categoria ou valor...", className="border-0 bg-light"),
                                ],
                                className="shadow-sm rounded-3",
                            ),
                            md=8,
                        ),
                        dbc.Col(
                            dbc.Button([html.I(className="bi bi-funnel me-2"), "Filtros"], id="btn-toggle-filtros", color="light", className="w-100 border shadow-sm"),
                            md=2,
                        ),
                        dbc.Col(
                            dcc.Dropdown(
                                id="ordenar-extrato",
                                options=[
                                    {"label": "Mais Recentes", "value": "data_desc"},
                                    {"label": "Mais Antigos", "value": "data_asc"},
                                    {"label": "Maior Valor", "value": "valor_desc"},
                                    {"label": "Menor Valor", "value": "valor_asc"},
                                ],
                                value="data_desc",
                                clearable=False,
                            ),
                            md=2,
                        ),
                    ],
                    className="align-items-center",
                )
            ),
            className="mb-3 border-0 shadow-sm",
        ),

        # Filtros Avançados
        dbc.Collapse(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H6("Filtros Avançados", className="fw-bold mb-3"),
                        dbc.Row(
                            [
                                dbc.Col(dcc.DatePickerRange(id="extrato-periodo", start_date=date.today().replace(day=1), end_date=date.today(), display_format="DD/MM/YYYY"), md=4),
                                dbc.Col(dcc.Dropdown(id="extrato-tipo", options=[{"label": "📈 Receita", "value": "receita"},{"label": "📉 Despesa", "value": "despesa"}], multi=True, placeholder="Todos"), md=4),
                                dbc.Col(dcc.Dropdown(id="extrato-status", options=[{"label": "Pago", "value": "pago"},{"label": "Recebido", "value": "recebido"},{"label": "Pendente", "value": "pendente"}], multi=True, placeholder="Todos"), md=4),
                            ],
                            className="mb-3",
                        ),
                        dbc.Row(
                            [
                                dbc.Col(dcc.Dropdown(id="extrato-categorias", options=[], multi=True, placeholder="Todas as categorias", persistence=True, persistence_type="session"), md=6),
                                dbc.Col(dbc.Input(id="valor-minimo", type="number", min=0, placeholder="Valor mínimo"), md=3),
                                dbc.Col(dbc.Input(id="valor-maximo", type="number", min=0, placeholder="Valor máximo"), md=3),
                            ],
                            className="mb-3",
                        ),
                        dbc.Button([html.I(className="bi bi-arrow-clockwise me-2"), "Limpar Filtros"], id="extrato-limpar-filtros", color="light", className="border", size="sm"),
                    ]
                ),
                className="border-0 shadow-sm",
            ),
            id="collapse-filtros-extrato",
            is_open=False,
            className="mb-4",
        ),

        # Listagem
        dbc.Card(
            [
                dbc.CardHeader(html.Span([html.I(className="bi bi-list-ul me-2"), "Transações"], className="fw-bold")),
                dbc.CardBody(html.Div(id="tabela-extrato")),
            ],
            className="shadow-sm border-0 mb-4",
        ),

        # Gráficos
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader(html.H6([html.I(className="bi bi-graph-up me-2"), "Evolução Financeira"]), className="bg-white border-0"),
                            dbc.CardBody(dcc.Graph(id="grafico-entradas-saidas", config={"displayModeBar": False})),
                        ],
                        className="shadow-sm border-0",
                    ),
                    md=8,
                ),
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader(html.H6([html.I(className="bi bi-pie-chart me-2"), "Por Categoria"]), className="bg-white border-0"),
                            dbc.CardBody(dcc.Graph(id="grafico-categorias", config={"displayModeBar": False})),
                        ],
                        className="shadow-sm border-0",
                    ),
                    md=4,
                ),
            ]
        ),
    ],
    fluid=True,
    className="py-3",
)

# =============================
# CALLBACKS
# =============================
@app.callback(
    Output("collapse-filtros-extrato", "is_open"),
    Input("btn-toggle-filtros", "n_clicks"),
    State("collapse-filtros-extrato", "is_open"),
)
def toggle_filtros(n, aberto):
    if n:
        return not aberto
    return aberto
