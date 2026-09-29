"""Página de gestão de Cartões de Crédito."""

from datetime import date

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
                                "Limite, fechamento, vencimento e faturas",
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
                                            html.I(className="bi bi-credit-card-2-front-fill me-2"),
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
            modal_novo_cartao(),
            modal_fatura(),
        ],
        fluid=True,
        className="py-4 px-3",
    )


def modal_novo_cartao() -> dbc.Modal:
    """Modal de criação de cartão."""
    return dbc.Modal(
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
    )


def modal_fatura() -> dbc.Modal:
    """Modal de visualização e pagamento de fatura."""
    return dbc.Modal(
        [
            dbc.ModalHeader(
                dbc.ModalTitle(
                    [
                        html.I(className="bi bi-receipt me-2 text-primary"),
                        "Fatura do Cartão",
                    ]
                ),
                close_button=True,
            ),
            dbc.ModalBody(
                [
                    dcc.Store(id="fatura-card-id", data=None),
                    html.Div(id="fatura-feedback"),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Mês", className="fw-bold"),
                                    dbc.Select(
                                        id="fatura-mes",
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
                                        id="fatura-ano",
                                        options=[
                                            {"label": str(year), "value": year}
                                            for year in range(2024, 2031)
                                        ],
                                        value=date.today().year,
                                    ),
                                ],
                                width=6,
                            ),
                        ],
                        className="mb-3",
                    ),
                    dcc.Loading(
                        html.Div(id="fatura-container"),
                        type="dot",
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label(
                                        "Conta de origem",
                                        className="fw-bold",
                                    ),
                                    dbc.Select(
                                        id="fatura-conta-origem",
                                        placeholder="Selecione a conta para pagar",
                                    ),
                                ],
                                width=8,
                            ),
                            dbc.Col(
                                [
                                    dbc.Button(
                                        [
                                            html.I(className="bi bi-cash-coin me-1"),
                                            "Pagar Fatura",
                                        ],
                                        id="btn-pagar-fatura",
                                        color="success",
                                        className="w-100",
                                    ),
                                ],
                                width=4,
                                className="d-flex align-items-end",
                            ),
                        ],
                        className="mb-2",
                    ),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        [html.I(className="bi bi-x me-1"), "Fechar"],
                        id="btn-fechar-fatura",
                        color="secondary",
                        outline=True,
                        n_clicks=0,
                    )
                ]
            ),
        ],
        id="modal-fatura",
        is_open=False,
        size="xl",
        backdrop="static",
    )
