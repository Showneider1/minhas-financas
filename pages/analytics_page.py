"""Página de Analytics e Relatórios visuais."""

from datetime import date

import dash_bootstrap_components as dbc
from dash import dcc, html


def layout():
    """Layout da página de analytics."""
    current_year = date.today().year
    years = list(range(current_year - 5, current_year + 1))

    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2(
                                [
                                    html.I(className="bi bi-graph-up-arrow me-2"),
                                    "Analytics",
                                ],
                                className="mb-0 fw-bold",
                            ),
                            html.P(
                                "Despesas por categoria e fluxo mensal",
                                className="text-muted mb-0",
                            ),
                        ],
                        width=True,
                    ),
                    dbc.Col(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Mês", className="fw-bold"),
                                            dbc.Select(
                                                id="analytics-month",
                                                options=[
                                                    {"label": "Janeiro", "value": 1},
                                                    {"label": "Fevereiro", "value": 2},
                                                    {"label": "Março", "value": 3},
                                                    {"label": "Abril", "value": 4},
                                                    {"label": "Maio", "value": 5},
                                                    {"label": "Junho", "value": 6},
                                                    {"label": "Julho", "value": 7},
                                                    {"label": "Agosto", "value": 8},
                                                    {"label": "Setembro", "value": 9},
                                                    {"label": "Outubro", "value": 10},
                                                    {"label": "Novembro", "value": 11},
                                                    {"label": "Dezembro", "value": 12},
                                                ],
                                                value=date.today().month,
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Ano", className="fw-bold"),
                                            dbc.Select(
                                                id="analytics-year",
                                                options=[
                                                    {"label": str(year), "value": year}
                                                    for year in years
                                                ],
                                                value=current_year,
                                            ),
                                        ],
                                        width=6,
                                    ),
                                ],
                                className="g-2",
                            ),
                        ],
                        width="auto",
                    ),
                ],
                align="center",
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.I(className="bi bi-pie-chart-fill me-2"),
                                            "Despesas por Categoria",
                                        ],
                                        className="bg-white fw-bold border-0 pb-0",
                                    ),
                                    dbc.CardBody(
                                        [
                                            dcc.Loading(
                                                dcc.Graph(
                                                    id="analytics-expenses-category",
                                                    config={"displayModeBar": False},
                                                    style={"height": "360px"},
                                                ),
                                                type="dot",
                                            )
                                        ],
                                        className="pt-2",
                                    ),
                                ],
                                className="shadow-sm border-0 h-100",
                            ),
                        ],
                        width=12,
                        lg=5,
                        className="mb-3",
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.I(className="bi bi-bar-chart-line-fill me-2"),
                                            "Fluxo Mensal",
                                        ],
                                        className="bg-white fw-bold border-0 pb-0",
                                    ),
                                    dbc.CardBody(
                                        [
                                            dcc.Loading(
                                                dcc.Graph(
                                                    id="analytics-cash-flow",
                                                    config={"displayModeBar": False},
                                                    style={"height": "360px"},
                                                ),
                                                type="dot",
                                            )
                                        ],
                                        className="pt-2",
                                    ),
                                ],
                                className="shadow-sm border-0 h-100",
                            ),
                        ],
                        width=12,
                        lg=7,
                        className="mb-3",
                    ),
                ],
                className="mb-3",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Small(
                                "TRANSFER não entra em Receitas ou Despesas.",
                                className="text-muted",
                            )
                        ],
                        width=12,
                    )
                ]
            ),
        ],
        fluid=True,
        className="py-4 px-3",
    )
