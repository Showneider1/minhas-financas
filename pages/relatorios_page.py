"""
Pagina de Relatorios Financeiros.
Layout completo com:
- Relatorio Mensal e Anual com graficos Plotly
- Score de Saude Financeira com gauge interativo
- Filtros de periodo e tipo
- Exportacao para CSV e Excel
"""
import dash_bootstrap_components as dbc
from dash import html, dcc
from datetime import date


def _section_title(icon: str, title: str) -> html.Div:
    """Cabecalho de secao com icone Bootstrap Icons."""
    return html.Div(
        [
            html.I(className=f"bi {icon} me-2 fs-5"),
            html.Span(title, className="fw-semibold fs-5"),
        ],
        className="d-flex align-items-center mb-3",
    )


def _kpi_card(title: str, kpi_id: str, color: str, icon: str = "") -> dbc.Col:
    """Card KPI reutilizavel para a secao de resumo."""
    return dbc.Col(
        dbc.Card(
            dbc.CardBody(
                [
                    html.Div(
                        [
                            html.I(className=f"bi {icon} me-2 fs-4"),
                            html.Span(title, className="text-muted small fw-semibold"),
                        ],
                        className="mb-2",
                    ),
                    html.H4(id=kpi_id, children="R$ ...", className=f"fw-bold mb-0 {color}"),
                ]
            ),
            className="shadow-sm h-100",
        ),
        width=12, sm=6, lg=3, className="mb-3",
    )


# ------------------------------------------------------------------ #
# LAYOUT PRINCIPAL                                                       #
# ------------------------------------------------------------------ #

layout = dbc.Container(
    [
        # Store para dados calculados
        dcc.Store(id="store-relatorio-data"),

        # ── Cabecalho ──────────────────────────────────────────────── #
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H2("Relatorios", className="mb-0 fw-bold"),
                        html.P(
                            "Analise completa das suas financas",
                            className="text-muted mb-0",
                        ),
                    ],
                    width=True,
                ),
                dbc.Col(
                    dbc.ButtonGroup(
                        [
                            dbc.Button(
                                [html.I(className="bi bi-file-earmark-spreadsheet me-1"), "Excel"],
                                id="btn-export-excel",
                                color="success",
                                outline=True,
                                size="sm",
                            ),
                            dbc.Button(
                                [html.I(className="bi bi-filetype-csv me-1"), "CSV"],
                                id="btn-export-csv",
                                color="secondary",
                                outline=True,
                                size="sm",
                            ),
                        ]
                    ),
                    width="auto",
                    className="d-flex align-items-center",
                ),
            ],
            align="center",
            className="mb-4",
        ),

        # ── Filtros ─────────────────────────────────────────────────── #
        dbc.Card(
            dbc.CardBody(
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Label("Periodo", className="fw-semibold small"),
                                dcc.DatePickerRange(
                                    id="relatorio-date-range",
                                    display_format="DD/MM/YYYY",
                                    start_date=date.today().replace(day=1),
                                    end_date=date.today(),
                                    className="w-100",
                                ),
                            ],
                            width=12, md=5,
                        ),
                        dbc.Col(
                            [
                                html.Label("Tipo de Relatorio", className="fw-semibold small"),
                                dbc.Select(
                                    id="relatorio-tipo",
                                    options=[
                                        {"label": "Mensal",        "value": "monthly"},
                                        {"label": "Anual",         "value": "annual"},
                                        {"label": "Personalizado", "value": "custom"},
                                    ],
                                    value="monthly",
                                ),
                            ],
                            width=12, md=3,
                        ),
                        dbc.Col(
                            [
                                html.Label("Ano", className="fw-semibold small"),
                                dbc.Select(
                                    id="relatorio-ano",
                                    options=[
                                        {"label": str(y), "value": str(y)}
                                        for y in range(date.today().year, date.today().year - 5, -1)
                                    ],
                                    value=str(date.today().year),
                                ),
                            ],
                            width=12, md=2,
                        ),
                        dbc.Col(
                            [
                                html.Label("\u00a0", className="d-block"),
                                dbc.Button(
                                    [html.I(className="bi bi-search me-1"), "Gerar"],
                                    id="btn-gerar-relatorio",
                                    color="primary",
                                    className="w-100",
                                ),
                            ],
                            width=12, md=2,
                        ),
                    ],
                    className="g-3",
                )
            ),
            className="shadow-sm mb-4",
        ),

        # ── KPIs de Resumo ───────────────────────────────────────────── #
        dbc.Row(
            [
                _kpi_card("Total Receitas",  "rel-kpi-receitas",  "text-success", "bi-arrow-up-circle-fill"),
                _kpi_card("Total Despesas",  "rel-kpi-despesas",  "text-danger",  "bi-arrow-down-circle-fill"),
                _kpi_card("Saldo do Periodo","rel-kpi-saldo",     "text-primary", "bi-wallet2"),
                _kpi_card("Transacoes",      "rel-kpi-transacoes","text-secondary","bi-list-check"),
            ],
            className="mb-4",
        ),

        # ── Score de Saude Financeira ─────────────────────────────────── #
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader(
                            _section_title("bi-heart-pulse-fill", "Score de Saude Financeira"),
                            className="bg-white fw-bold border-0 pb-0",
                        ),
                        dbc.CardBody(
                            dcc.Loading(
                                html.Div(id="rel-health-score-content"),
                                type="dot",
                            )
                        ),
                    ],
                    className="shadow-sm",
                ),
                width=12,
                className="mb-4",
            )
        ),

        # ── Graficos Principais ─────────────────────────────────────── #
        dbc.Row(
            [
                # Evolucao Mensal (linha)
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                _section_title("bi-graph-up-arrow", "Evolucao de Receitas x Despesas"),
                                className="bg-white fw-bold border-0 pb-0",
                            ),
                            dbc.CardBody(
                                dcc.Loading(
                                    dcc.Graph(
                                        id="rel-grafico-evolucao",
                                        config={"displayModeBar": False},
                                        style={"height": "300px"},
                                    ),
                                    type="dot",
                                )
                            ),
                        ],
                        className="shadow-sm",
                    ),
                    width=12, lg=8, className="mb-4",
                ),

                # Distribuicao por Categoria (pizza)
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                _section_title("bi-pie-chart-fill", "Despesas por Categoria"),
                                className="bg-white fw-bold border-0 pb-0",
                            ),
                            dbc.CardBody(
                                dcc.Loading(
                                    dcc.Graph(
                                        id="rel-grafico-categorias",
                                        config={"displayModeBar": False},
                                        style={"height": "300px"},
                                    ),
                                    type="dot",
                                )
                            ),
                        ],
                        className="shadow-sm",
                    ),
                    width=12, lg=4, className="mb-4",
                ),
            ]
        ),

        # ── Comparativo Mensal (barras agrupadas) ────────────────────── #
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader(
                            _section_title("bi-bar-chart-fill", "Comparativo Mensal - Ano Completo"),
                            className="bg-white fw-bold border-0 pb-0",
                        ),
                        dbc.CardBody(
                            dcc.Loading(
                                dcc.Graph(
                                    id="rel-grafico-anual",
                                    config={"displayModeBar": False},
                                    style={"height": "300px"},
                                ),
                                type="dot",
                            )
                        ),
                    ],
                    className="shadow-sm",
                ),
                width=12,
                className="mb-4",
            )
        ),

        # ── Tabela de Transacoes ─────────────────────────────────────── #
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardHeader(
                            dbc.Row(
                                [
                                    dbc.Col(
                                        _section_title("bi-table", "Transacoes do Periodo"),
                                        width=True,
                                    ),
                                    dbc.Col(
                                        dbc.Input(
                                            id="rel-tabela-busca",
                                            placeholder="Buscar transacao...",
                                            size="sm",
                                            className="w-auto",
                                        ),
                                        width="auto",
                                    ),
                                ],
                                align="center",
                            ),
                            className="bg-white border-0 pb-0",
                        ),
                        dbc.CardBody(
                            dcc.Loading(
                                html.Div(id="rel-tabela-transacoes"),
                                type="dot",
                            )
                        ),
                    ],
                    className="shadow-sm",
                ),
                width=12,
                className="mb-4",
            )
        ),

        # Download invisivel para exportacao
        dcc.Download(id="rel-download"),
    ],
    fluid=True,
    className="py-4",
)
