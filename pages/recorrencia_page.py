"""
Página de Recorrências de Contas.
Exibe contas recorrentes ativas e permite criar assinatura/conta fixa,
pausar e cancelar via BillRecurrenceService.
"""

from datetime import date

import dash_bootstrap_components as dbc
from dash import dcc, html

BILL_TYPE_OPTIONS = [
    {"label": "Despesa", "value": "payable"},
    {"label": "Receita", "value": "receivable"},
]

RECURRENCE_OPTIONS = [
    {"label": "Nenhuma", "value": "none"},
    {"label": "Mensal", "value": "monthly"},
    {"label": "Trimestral", "value": "quarterly"},
    {"label": "Semanal", "value": "weekly"},
    {"label": "Anual", "value": "yearly"},
]


modal_recurrence = dbc.Modal(
    [
        dbc.ModalHeader(
            dbc.ModalTitle(
                [
                    html.I(className="bi bi-repeat me-2 text-primary"),
                    html.Span("Nova Recorrência", id="rec-modal-title"),
                ]
            ),
            close_button=True,
        ),
        dbc.ModalBody(
            [
                dcc.Store(id="rec-edit-id", data=None),
                dbc.Alert(
                    id="rec-modal-alert",
                    is_open=False,
                    color="danger",
                    dismissable=True,
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Nome *", className="fw-bold"),
                                dbc.Input(
                                    id="rec-input-name",
                                    placeholder="Ex: Netflix, Aluguel...",
                                    maxLength=200,
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
                                dbc.Label("Tipo *", className="fw-bold"),
                                dbc.Select(
                                    id="rec-input-type",
                                    options=BILL_TYPE_OPTIONS,
                                    value="payable",
                                ),
                            ],
                            width=6,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Valor (R$) *", className="fw-bold"),
                                dbc.InputGroup(
                                    [
                                        dbc.InputGroupText("R$"),
                                        dbc.Input(
                                            id="rec-input-amount",
                                            type="number",
                                            min=0.01,
                                            step=0.01,
                                            placeholder="0,00",
                                        ),
                                    ]
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
                                dbc.Label("Dia de Vencimento", className="fw-bold"),
                                dcc.DatePickerSingle(
                                    id="rec-input-due-date",
                                    display_format="DD/MM/YYYY",
                                    date=date.today(),
                                ),
                            ],
                            width=6,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Recorrência", className="fw-bold"),
                                dbc.Select(
                                    id="rec-input-recurrence",
                                    options=RECURRENCE_OPTIONS,
                                    value="monthly",
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
                                dbc.Label("Conta", className="fw-bold"),
                                dbc.Select(
                                    id="rec-input-account",
                                    options=[{"label": "Selecione...", "value": ""}],
                                    placeholder="Conta vinculada",
                                ),
                            ],
                            width=6,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Categoria", className="fw-bold"),
                                dbc.Select(
                                    id="rec-input-category",
                                    options=[{"label": "Selecione...", "value": ""}],
                                    placeholder="Categoria",
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
                                    id="rec-input-notes",
                                    rows=2,
                                    placeholder="Opcional",
                                    maxLength=500,
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
                    id="rec-btn-cancel",
                    color="secondary",
                    outline=True,
                ),
                dbc.Button(
                    [html.I(className="bi bi-check2 me-1"), "Salvar"],
                    id="rec-btn-save",
                    color="primary",
                ),
            ]
        ),
    ],
    id="recurrence-modal",
    is_open=False,
    size="lg",
    backdrop="static",
)


def layout():
    return dbc.Container(
        [
            dbc.Alert(
                id="rec-alert",
                is_open=False,
                color="danger",
                dismissable=True,
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2(
                                [html.I(className="bi bi-repeat me-2"), "Recorrências"],
                                className="mb-0 fw-bold",
                            ),
                            html.P(
                                "Contas e assinaturas fixas",
                                className="text-muted mb-0",
                            ),
                        ],
                        width=True,
                    ),
                    dbc.Col(
                        [
                            dbc.Button(
                                [html.I(className="bi bi-plus-circle me-2"), "Nova Recorrência"],
                                id="rec-btn-new",
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
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        [
                                            html.I(className="bi bi-list-check me-2"),
                                            "Contas Ativas",
                                        ],
                                        className="bg-white fw-bold border-0 pb-0",
                                    ),
                                    dbc.CardBody(
                                        [
                                            dcc.Loading(
                                                html.Div(id="recurrence-table"),
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
            modal_recurrence,
        ],
        fluid=True,
        className="py-4 px-3",
    )
