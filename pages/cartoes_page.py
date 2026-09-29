"""Página de gestão de Cartões de Crédito."""

import dash_bootstrap_components as dbc
from dash import dcc, html


def layout():
    """Layout da página de cartões."""
    return dbc.Container(
        [
            dcc.Store(id="cartoes-reload-trigger", data=0),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2(
                                [
                                    html.I(className="bi bi-credit-card-fill me-2"),
                                    "Cartões de Crédito",
                                ],
                                className="mb-0 fw-bold",
                            ),
                            html.P(
                                "Limite, fechamento, vencimento e compras",
                                className="text-muted mb-0",
                            ),
                        ],
                        width=True,
                    ),
                    dbc.Col(
                        [
                            dbc.Button(
                                [
                                    html.I(className="bi bi-plus-circle me-2"),
                                    "Novo Cartão",
                                ],
                                id="btn-open-credit-card-modal",
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
                id="cartoes-feedback",
                is_open=False,
                color="danger",
                dismissable=True,
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.I(
                                                className=("bi bi-credit-card-2-front-fill me-2")
                                            ),
                                            "Meus cartões",
                                        ],
                                        className="bg-white fw-bold border-0 pb-0",
                                    ),
                                    dbc.CardBody(
                                        [
                                            dcc.Loading(
                                                html.Div(id="cartoes-list-container"),
                                                type="dot",
                                            ),
                                        ],
                                        className="pt-2",
                                    ),
                                ],
                                className="shadow-sm border-0",
                            ),
                        ],
                        width=12,
                    ),
                ],
                className="mb-3",
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle(
                            [
                                html.I(className="bi bi-credit-card-fill me-2 text-primary"),
                                "Novo Cartão",
                            ]
                        ),
                        close_button=True,
                    ),
                    dbc.ModalBody(
                        [
                            html.Div(id="credit-card-feedback"),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Nome do cartão *", className="fw-bold"),
                                            dbc.Input(
                                                id="credit-card-nome",
                                                placeholder="Ex: Nubank, Itaú...",
                                                maxLength=100,
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
                                            dbc.Label("Limite total (R$) *", className="fw-bold"),
                                            dbc.InputGroup(
                                                [
                                                    dbc.InputGroupText("R$"),
                                                    dbc.Input(
                                                        id="credit-card-limite",
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
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label(
                                                "Dia de fechamento *",
                                                className="fw-bold",
                                            ),
                                            dbc.Input(
                                                id="credit-card-fechamento",
                                                type="number",
                                                min=1,
                                                max=31,
                                                step=1,
                                                placeholder="Ex: 3",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label(
                                                "Dia de vencimento *",
                                                className="fw-bold",
                                            ),
                                            dbc.Input(
                                                id="credit-card-vencimento",
                                                type="number",
                                                min=1,
                                                max=31,
                                                step=1,
                                                placeholder="Ex: 10",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            html.Small(
                                "Compras no dia ou após o fechamento entram na fatura seguinte.",
                                className="text-muted",
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                [html.I(className="bi bi-x me-1"), "Cancelar"],
                                id="btn-cancel-credit-card-modal",
                                color="secondary",
                                outline=True,
                                n_clicks=0,
                            ),
                            dbc.Button(
                                [html.I(className="bi bi-check2 me-1"), "Salvar Cartão"],
                                id="btn-save-credit-card-modal",
                                color="primary",
                                n_clicks=0,
                            ),
                        ]
                    ),
                ],
                id="modal-credit-card",
                is_open=False,
                size="lg",
                backdrop="static",
            ),
        ],
        fluid=True,
        className="py-4 px-3",
    )
