"""
Modal global de nova transação.

Suporta:
- Receita
- Despesa
- Transferência entre contas
"""

from datetime import date

import dash_bootstrap_components as dbc
from dash import dcc, html


def create_transaction_modal():
    """Cria o modal unificado de novo lançamento."""
    return dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle(
                    [
                        html.I(className="bi bi-plus-circle me-2 text-primary"),
                        html.Span("Novo Lançamento", id="modal-header-title"),
                    ]
                ),
                close_button=True,
            ),
            dbc.ModalBody(
                [
                    html.Div(id="feedback-transacao"),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Tipo", className="fw-bold"),
                                    dbc.RadioItems(
                                        id="tipo-lancamento",
                                        options=[
                                            {
                                                "label": html.Span(
                                                    [
                                                        html.I(
                                                            className=(
                                                                "bi bi-arrow-up-circle-fill "
                                                                "text-success me-1"
                                                            )
                                                        ),
                                                        " Receita",
                                                    ]
                                                ),
                                                "value": "INCOME",
                                            },
                                            {
                                                "label": html.Span(
                                                    [
                                                        html.I(
                                                            className=(
                                                                "bi bi-arrow-down-circle-fill "
                                                                "text-danger me-1"
                                                            )
                                                        ),
                                                        " Despesa",
                                                    ]
                                                ),
                                                "value": "EXPENSE",
                                            },
                                            {
                                                "label": html.Span(
                                                    [
                                                        html.I(
                                                            className=(
                                                                "bi bi-arrow-left-right "
                                                                "text-primary me-1"
                                                            )
                                                        ),
                                                        " Transferência",
                                                    ]
                                                ),
                                                "value": "TRANSFER",
                                            },
                                        ],
                                        value="EXPENSE",
                                        inline=True,
                                        className="mt-1",
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
                                                id="input-valor",
                                                placeholder="0,00",
                                                type="text",
                                                className="text-end fs-5 fw-bold",
                                            ),
                                        ]
                                    ),
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Descrição", className="fw-bold"),
                                    dbc.Input(
                                        id="input-descricao",
                                        placeholder="Ex: Mercado, Salário...",
                                        maxLength=255,
                                    ),
                                ],
                                width=6,
                            ),
                        ],
                        className="mb-3",
                    ),
                    html.Div(
                        id="standard-section",
                        children=[
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label("Categoria", className="fw-bold"),
                                            dbc.Select(
                                                id="select-categoria",
                                                placeholder="Selecione...",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label("Conta / Cartão", className="fw-bold"),
                                            dbc.Select(
                                                id="select-conta",
                                                placeholder="Selecione...",
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
                                            dbc.Label(
                                                "Parcela Atual",
                                                className="fw-bold small",
                                            ),
                                            dbc.Input(
                                                id="input-parcela-atual",
                                                type="number",
                                                value=1,
                                                min=1,
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label(
                                                "Total de Parcelas",
                                                className="fw-bold small",
                                            ),
                                            dbc.Input(
                                                id="input-total-parcelas",
                                                type="number",
                                                value=1,
                                                min=1,
                                            ),
                                        ],
                                        width=6,
                                    ),
                                ],
                                className="mb-3",
                            ),
                            dbc.Checklist(
                                options=[
                                    {
                                        "label": " É assinatura/despesa fixa?",
                                        "value": "recorrente",
                                    }
                                ],
                                value=[],
                                id="check-recorrencia",
                                switch=True,
                                className="mb-3",
                            ),
                        ],
                    ),
                    html.Div(
                        id="transfer-section",
                        style={"display": "none"},
                        children=[
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label(
                                                "Conta Origem",
                                                className="fw-bold",
                                            ),
                                            dbc.Select(
                                                id="select-conta",
                                                placeholder="Selecione a conta de origem",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dbc.Label(
                                                "Conta Destino",
                                                className="fw-bold",
                                            ),
                                            dbc.Select(
                                                id="select-conta-destino",
                                                placeholder="Selecione a conta de destino",
                                            ),
                                        ],
                                        width=6,
                                    ),
                                ],
                                className="mb-3",
                            ),
                        ],
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Data Compra", className="fw-bold small"),
                                    dcc.DatePickerSingle(
                                        id="data-compra",
                                        display_format="DD/MM/YYYY",
                                        date=date.today(),
                                        className="d-block",
                                    ),
                                ],
                                width=4,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Vencimento", className="fw-bold small"),
                                    dcc.DatePickerSingle(
                                        id="data-vencimento",
                                        display_format="DD/MM/YYYY",
                                        date=date.today(),
                                        className="d-block",
                                    ),
                                ],
                                width=4,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Data Pagamento", className="fw-bold small"),
                                    dcc.DatePickerSingle(
                                        id="data-pagamento",
                                        display_format="DD/MM/YYYY",
                                        date=date.today(),
                                        className="d-block",
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
                                    dbc.Switch(
                                        id="switch-pago",
                                        label="Lançamento já foi pago/recebido",
                                        value=True,
                                    ),
                                ],
                                width=12,
                            )
                        ],
                        className="mb-3",
                    ),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        [html.I(className="bi bi-x me-1"), "Cancelar"],
                        id="btn-cancelar-modal",
                        color="secondary",
                        outline=True,
                        n_clicks=0,
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-check2 me-1"), "Salvar Lançamento"],
                        id="btn-salvar-lancamento",
                        color="primary",
                        n_clicks=0,
                    ),
                ]
            ),
        ],
        id="modal-novo-lancamento",
        is_open=False,
        size="lg",
        backdrop="static",
    )
