"""
Página de Investimentos.
Exibe carteira derivada do InvestmentService e permite registrar
compra/venda/proventos/split via serviço.
"""

from datetime import date

import dash_bootstrap_components as dbc
from dash import dcc, html

OP_TYPE_OPTIONS = [
    {"label": "Compra", "value": "BUY"},
    {"label": "Venda", "value": "SELL"},
    {"label": "Provento / JCP", "value": "DIVIDEND"},
    {"label": "Split", "value": "SPLIT"},
]


modal_investimento = dbc.Modal(
    [
        dbc.ModalHeader(
            dbc.ModalTitle(
                [
                    html.I(className="bi bi-graph-up me-2 text-success"),
                    html.Span("Operação de Investimento", id="invest-modal-title"),
                ]
            ),
            close_button=True,
        ),
        dbc.ModalBody(
            [
                dcc.Store(id="invest-edit-id", data=None),
                dbc.Alert(
                    id="invest-modal-alert",
                    is_open=False,
                    color="danger",
                    dismissable=True,
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Tipo de Operação *", className="fw-bold"),
                                dbc.RadioItems(
                                    id="invest-op-type",
                                    options=OP_TYPE_OPTIONS,
                                    value="BUY",
                                    inline=True,
                                ),
                            ]
                        ),
                    ],
                    className="mb-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Ativo *", className="fw-bold"),
                                dbc.Select(
                                    id="invest-asset-select",
                                    options=[{"label": "Selecione...", "value": ""}],
                                    placeholder="Ticker do ativo",
                                ),
                            ],
                            width=6,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Conta *", className="fw-bold"),
                                dbc.Select(
                                    id="invest-account-select",
                                    options=[{"label": "Selecione...", "value": ""}],
                                    placeholder="Conta para liquidação",
                                ),
                            ],
                            width=6,
                        ),
                    ],
                    className="mb-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Quantidade *", className="fw-bold"),
                                dbc.Input(
                                    id="invest-qty",
                                    type="number",
                                    min=0,
                                    step="0.00000001",
                                    placeholder="Ex: 10",
                                ),
                            ],
                            width=4,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Preço Unitário (R$)", className="fw-bold"),
                                dbc.InputGroup(
                                    [
                                        dbc.InputGroupText("R$"),
                                        dbc.Input(
                                            id="invest-price",
                                            type="number",
                                            min=0,
                                            step=0.01,
                                            placeholder="0,00",
                                        ),
                                    ]
                                ),
                            ],
                            width=4,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Taxas (R$)", className="fw-bold"),
                                dbc.InputGroup(
                                    [
                                        dbc.InputGroupText("R$"),
                                        dbc.Input(
                                            id="invest-fees",
                                            type="number",
                                            min=0,
                                            step=0.01,
                                            value=0,
                                        ),
                                    ]
                                ),
                            ],
                            width=4,
                        ),
                    ],
                    className="mb-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Data da Operação", className="fw-bold"),
                                dcc.DatePickerSingle(
                                    id="invest-date",
                                    display_format="DD/MM/YYYY",
                                    date=date.today(),
                                ),
                            ],
                            width=6,
                        ),
                    ],
                    className="mb-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Observações", className="fw-bold"),
                                dbc.Textarea(
                                    id="invest-notes",
                                    rows=2,
                                    placeholder="Opcional",
                                    maxLength=255,
                                ),
                            ]
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
                    id="invest-btn-cancel",
                    color="secondary",
                    outline=True,
                ),
                dbc.Button(
                    [html.I(className="bi bi-check2 me-1"), "Salvar Operação"],
                    id="invest-btn-save",
                    color="primary",
                ),
            ]
        ),
    ],
    id="invest-operation-modal",
    is_open=False,
    size="lg",
    backdrop="static",
)


def layout():
    return dbc.Container(
        [
            dbc.Alert(
                id="invest-alert",
                is_open=False,
                color="danger",
                dismissable=True,
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2(
                                [html.I(className="bi bi-graph-up me-2"), "Investimentos"],
                                className="mb-0 fw-bold",
                            ),
                            html.P("Carteira e operações", className="text-muted mb-0"),
                        ],
                        width=True,
                    ),
                    dbc.Col(
                        [
                            dbc.Button(
                                [
                                    html.I(className="bi bi-arrow-repeat me-2"),
                                    "Atualizar Cotações",
                                ],
                                id="btn-update-prices",
                                color="primary",
                                outline=True,
                                className="fw-bold",
                            ),
                            dcc.Loading(
                                html.Div(id="invest-price-feedback"),
                                type="dot",
                                parent_style={"height": "24px"},
                            ),
                        ],
                        width="auto",
                        className="d-flex flex-column align-items-end",
                    ),
                    dbc.Col(
                        [
                            dbc.Button(
                                [html.I(className="bi bi-plus-circle me-2"), "Nova Operação"],
                                id="invest-btn-new",
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
                                    dbc.CardHeader(
                                        [html.I(className="bi bi-wallet2 me-2"), "Carteira"],
                                        className="bg-white fw-bold border-0 pb-0",
                                    ),
                                    dbc.CardBody(
                                        [
                                            dcc.Loading(
                                                html.Div(id="invest-portfolio-table"),
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
            modal_investimento,
        ],
        fluid=True,
        className="py-4 px-3",
    )
