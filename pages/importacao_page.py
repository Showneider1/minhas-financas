"""Página de Importação Bancária (OFX/CSV)."""

import dash_bootstrap_components as dbc
from dash import dcc, html


def layout():
    """Layout da página de importação."""
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.H2(
                                [
                                    html.I(className="bi bi-cloud-arrow-up me-2"),
                                    "Importação Bancária",
                                ],
                                className="mb-0 fw-bold",
                            ),
                            html.P(
                                "Importe extratos OFX/CSV e concilie antes de salvar",
                                className="text-muted mb-0",
                            ),
                        ],
                        width=True,
                    ),
                ],
                align="center",
                className="mb-4",
            ),
            dbc.Alert(
                id="import-feedback",
                is_open=False,
                color="danger",
                dismissable=True,
            ),
            dbc.Card(
                [
                    dbc.CardHeader(
                        [
                            html.I(className="bi bi-file-earmark-arrow-down me-2"),
                            "Upload do extrato",
                        ],
                        className="bg-white fw-bold border-0 pb-0",
                    ),
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dbc.Label(
                                                "Conta de destino",
                                                className="fw-bold",
                                            ),
                                            dbc.Select(
                                                id="import-account",
                                                placeholder="Selecione a conta",
                                            ),
                                        ],
                                        width=12,
                                        lg=6,
                                    ),
                                    dbc.Col(
                                        [
                                            dcc.Upload(
                                                id="import-upload",
                                                children=html.Div(
                                                    [
                                                        html.I(
                                                            className=(
                                                                "bi bi-cloud-arrow-up "
                                                                "fs-3 text-primary"
                                                            )
                                                        ),
                                                        html.Div(
                                                            "Arraste o arquivo aqui "
                                                            "ou clique para selecionar"
                                                        ),
                                                        html.Small(
                                                            "Formatos aceitos: .ofx e .csv",
                                                            className="text-muted",
                                                        ),
                                                    ],
                                                    className="text-center",
                                                ),
                                                style={
                                                    "width": "100%",
                                                    "height": "140px",
                                                    "lineHeight": "140px",
                                                    "borderWidth": "2px",
                                                    "borderStyle": "dashed",
                                                    "borderRadius": "12px",
                                                    "backgroundColor": "#f8f9fa",
                                                    "cursor": "pointer",
                                                },
                                                multiple=False,
                                            ),
                                        ],
                                        width=12,
                                        lg=6,
                                        className="d-flex align-items-stretch",
                                    ),
                                ],
                                className="mb-3",
                            ),
                            html.Div(
                                id="import-file-info",
                                className="text-muted small",
                            ),
                        ]
                    ),
                ],
                className="shadow-sm border-0 mb-3",
            ),
            dcc.Store(id="import-preview-store", data=[]),
            dcc.Loading(
                html.Div(id="import-preview-container"),
                type="dot",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Button(
                            [
                                html.I(className="bi bi-box-arrow-in-down me-1"),
                                "Processar Importação",
                            ],
                            id="btn-process-import",
                            color="success",
                            className="w-100",
                        ),
                        width=12,
                        lg=3,
                    ),
                ],
                className="mb-3",
            ),
        ],
        fluid=True,
        className="py-4 px-3",
    )
