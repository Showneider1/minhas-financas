from dash import html, dcc
import dash_bootstrap_components as dbc
from datetime import date
from .filters import dropdown_filter, date_range_filter

def modal_transaction(id="modal-novo-lancamento") -> dbc.Modal:
    """Modal padrão para criar/editar uma transação"""
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Adicionar Transação")),
            dbc.ModalBody(
                dbc.Container(
                    [
                        # Tipo de transação
                        dbc.Row(
                            dbc.Col(
                                dbc.RadioItems(
                                    id="tipo-lancamento",
                                    options=[
                                        {"label": " Entrada", "value": "receita"},
                                        {"label": " Saída", "value": "despesa"},
                                    ],
                                    value="despesa",
                                    inline=True,
                                    class_name="d-flex justify-content-center mb-4",
                                    inputClassName="btn-check",
                                    labelClassName="btn btn-outline-secondary rounded-pill px-4 mx-1 fw-bold",
                                    labelCheckedClassName="active btn-primary text-white border-0",
                                ),
                                width=12,
                            )
                        ),
                        # Valor e data
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Label("Valor Total", className="small text-muted fw-bold"),
                                        dbc.Input(id="input-valor", placeholder="0,00", type="text")
                                    ],
                                    md=6
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Data", className="small text-muted fw-bold"),
                                        dcc.DatePickerSingle(id="data-lancamento", date=date.today())
                                    ],
                                    md=6
                                )
                            ]
                        ),
                        # Descrição
                        dbc.Row(
                            dbc.Col(
                                dbc.Input(id="input-descricao", placeholder="Descrição"),
                                width=12
                            )
                        ),
                        # Categoria
                        dbc.Row(
                            dbc.Col(
                                dbc.Select(
                                    id="select-categoria",
                                    options=[
                                        {"label": "Casa", "value": "casa"},
                                        {"label": "Alimentação", "value": "alimentacao"},
                                    ]
                                ),
                                width=12
                            )
                        )
                    ],
                    fluid=True
                )
            ),
            dbc.ModalFooter(
                [
                    dbc.Button("Cancelar", id="btn-cancelar-modal", color="light"),
                    dbc.Button("Salvar Lançamento", id="btn-salvar-lancamento", color="success"),
                ]
            ),
        ],
        id=id,
        is_open=False,
        size="lg",
        centered=True,
    )
