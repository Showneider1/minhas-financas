"""
Página de Caixinhas (Virtual Vaults/Envelopes).
"""
from datetime import date

import dash_bootstrap_components as dbc
from dash import dcc, html

modal_vault = dbc.Modal(
    [
        dbc.ModalHeader(
            dbc.ModalTitle(
                [
                    html.I(className="bi bi-piggy-bank me-2 text-success"),
                    html.Span("Gerenciar Caixinha", id="vault-modal-title"),
                ]
            ),
            close_button=True,
        ),
        dbc.ModalBody(
            [
                dcc.Store(id="vault-edit-id", data=None),
                dbc.Alert(
                    id="vault-modal-alert",
                    is_open=False,
                    color="danger",
                    dismissable=True,
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Caixinha", className="fw-bold"),
                                dbc.Select(
                                    id="vault-select",
                                    options=[{"label": "Selecione...", "value": ""}],
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
                                dbc.Label("Valor (R$)", className="fw-bold"),
                                dbc.InputGroup(
                                    [
                                        dbc.InputGroupText("R$"),
                                        dbc.Input(
                                            id="vault-amount",
                                            type="number",
                                            min=0,
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
                    id="vault-btn-cancel",
                    color="secondary",
                    outline=True,
                ),
                dbc.Button(
                    [html.I(className="bi bi-arrow-down-circle me-1"), "Resgatar"],
                    id="vault-btn-withdraw",
                    color="danger",
                ),
                dbc.Button(
                    [html.I(className="bi bi-arrow-up-circle me-1"), "Guardar"],
                    id="vault-btn-allocate",
                    color="success",
                ),
            ]
        ),
    ],
    id="vault-modal",
    is_open=False,
    size="md",
    backdrop="static",
)


def layout():
    return dbc.Container(
        [
            dbc.Alert(
                id="vault-alert",
                is_open=False,
                color="danger",
                dismissable=True,
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2(
                                [html.I(className="bi bi-piggy-bank me-2"), "Caixinhas"],
                                className="mb-0 fw-bold",
                            ),
                            html.P("Segregue seu saldo em objetivos", className="text-muted mb-0"),
                        ],
                        width=True,
                    ),
                    dbc.Col(
                        [
                            dbc.Button(
                                [html.I(className="bi bi-plus-circle me-2"), "Nova Caixinha"],
                                id="vault-btn-new",
                                color="success",
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
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardBody(
                                        dcc.Loading(
                                            html.Div(id="vaults-cards-container"),
                                            type="dot",
                                        )
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
            modal_vault,
        ],
        fluid=True,
        className="py-4 px-3",
    )
