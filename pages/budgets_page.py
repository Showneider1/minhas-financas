"""Página de Orçamentos por Categoria."""

from datetime import date

import dash_bootstrap_components as dbc
from dash import dcc, html


def layout():
    """Layout da página de orçamentos."""
    today = date.today()
    years = list(range(today.year - 2, today.year + 3))

    return dbc.Container(
        [
            dcc.Store(id="budgets-reload-trigger", data=0),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2(
                                [
                                    html.I(className="bi bi-wallet2 me-2"),
                                    "Orçamentos",
                                ],
                                className="mb-0 fw-bold",
                            ),
                            html.P(
                                "Limites de gastos por categoria",
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
                                                id="budget-month",
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
                                                value=today.month,
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Ano", className="fw-bold"),
                                            dbc.Select(
                                                id="budget-year",
                                                options=[
                                                    {"label": str(year), "value": year}
                                                    for year in years
                                                ],
                                                value=today.year,
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
                    dbc.Col(
                        [
                            dbc.Button(
                                [
                                    html.I(className="bi bi-plus-circle me-1"),
                                    "Novo Orçamento",
                                ],
                                id="btn-open-budget-modal",
                                color="primary",
                                className="fw-bold",
                            ),
                        ],
                        width="auto",
                        className="d-flex align-items-center",
                    ),
                ],
                align="center",
                className="mb-4",
            ),
            dbc.Alert(
                id="budget-feedback",
                is_open=False,
                color="danger",
                dismissable=True,
            ),
            dcc.Loading(
                html.Div(id="budget-list-container"),
                type="dot",
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle(
                            [
                                html.I(className="bi bi-wallet2 me-2 text-primary"),
                                "Novo Orçamento",
                            ]
                        ),
                        close_button=True,
                    ),
                    dbc.ModalBody(
                        [
                            html.Div(id="budget-modal-feedback"),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Categoria *", className="fw-bold"),
                                            dbc.Select(
                                                id="budget-category",
                                                placeholder="Selecione a categoria",
                                            ),
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Valor Limite (R$) *", className="fw-bold"),
                                            dbc.InputGroup(
                                                [
                                                    dbc.InputGroupText("R$"),
                                                    dbc.Input(
                                                        id="budget-amount",
                                                        type="number",
                                                        min=0.01,
                                                        step=0.01,
                                                        placeholder="0,00",
                                                    ),
                                                ]
                                            ),
                                        ],
                                        width=12,
                                    ),
                                ],
                                className="mb-3",
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                [html.I(className="bi bi-x me-1"), "Cancelar"],
                                id="btn-cancel-budget-modal",
                                color="secondary",
                                outline=True,
                                n_clicks=0,
                            ),
                            dbc.Button(
                                [html.I(className="bi bi-check2 me-1"), "Salvar"],
                                id="btn-save-budget-modal",
                                color="primary",
                                n_clicks=0,
                            ),
                        ]
                    ),
                ],
                id="budget-modal",
                is_open=False,
                size="lg",
                backdrop="static",
            ),
        ],
        fluid=True,
        className="py-4 px-3",
    )
