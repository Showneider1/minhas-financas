"""
Extrato de Lancamentos v2
Melhorias:
- Botao "Novo Lancamento" conectado ao modal global (btn-novo-lancamento)
- Adiciona busca textual em tempo real
- Paginacao (30 por pagina)
- Stores para edicao e exclusao via modal global
- Modal confirmacao de exclusao proprio
- Toast de feedback
- Filtro de periodo expandido para incluir pendentes do mes
"""

from datetime import date

import dash_bootstrap_components as dbc
from dash import dcc, html

layout = dbc.Container(
    [
        dcc.Store(id="extrato-reload-trigger", data=0),
        dcc.Store(id="extrato-page-current", data=1),
        dcc.Store(id="extrato-del-id", data=None),
        dcc.Download(id="download-dataframe-csv"),
        # Cabecalho
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H2("Extrato de Lancamentos", className="fw-bold text-primary"),
                        html.P(
                            "Consulte e gerencie todo o seu historico financeiro.",
                            className="text-muted",
                        ),
                    ],
                    width=12,
                    md=8,
                ),
                dbc.Col(
                    [
                        # CORRECAO: ID único do Extrato, ligado ao modal global via callback
                        dbc.Button(
                            [html.I(className="bi bi-plus-lg me-2"), "Novo Lançamento"],
                            id="btn-novo-lancamento-extrato",
                            color="success",
                            className="mt-2 w-100",
                        ),
                    ],
                    width=12,
                    md=4,
                    className="text-end",
                ),
            ],
            className="mb-4 mt-3",
        ),
        # Filtros
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Label("Mês", className="fw-bold small"),
                                        dbc.Select(
                                            id="extrato-filter-month",
                                            options=[
                                                {
                                                    "label": "Janeiro",
                                                    "value": 1,
                                                },
                                                {
                                                    "label": "Fevereiro",
                                                    "value": 2,
                                                },
                                                {
                                                    "label": "Março",
                                                    "value": 3,
                                                },
                                                {
                                                    "label": "Abril",
                                                    "value": 4,
                                                },
                                                {
                                                    "label": "Maio",
                                                    "value": 5,
                                                },
                                                {
                                                    "label": "Junho",
                                                    "value": 6,
                                                },
                                                {
                                                    "label": "Julho",
                                                    "value": 7,
                                                },
                                                {
                                                    "label": "Agosto",
                                                    "value": 8,
                                                },
                                                {
                                                    "label": "Setembro",
                                                    "value": 9,
                                                },
                                                {
                                                    "label": "Outubro",
                                                    "value": 10,
                                                },
                                                {
                                                    "label": "Novembro",
                                                    "value": 11,
                                                },
                                                {
                                                    "label": "Dezembro",
                                                    "value": 12,
                                                },
                                            ],
                                            value=date.today().month,
                                        ),
                                    ],
                                    width=6,
                                    md=2,
                                    className="mb-2",
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Ano", className="fw-bold small"),
                                        dbc.Select(
                                            id="extrato-filter-year",
                                            options=[
                                                {"label": str(year), "value": year}
                                                for year in range(
                                                    date.today().year - 5,
                                                    date.today().year + 2,
                                                )
                                            ],
                                            value=date.today().year,
                                        ),
                                    ],
                                    width=6,
                                    md=2,
                                    className="mb-2",
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Busca", className="fw-bold small"),
                                        dbc.Input(
                                            id="extrato-filter-search",
                                            placeholder="Descricao, categoria...",
                                            debounce=True,
                                            type="text",
                                        ),
                                    ],
                                    width=12,
                                    md=3,
                                    className="mb-2",
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Conta Bancaria", className="fw-bold small"),
                                        dbc.Select(
                                            id="extrato-filter-account",
                                            options=[],
                                            placeholder="Todas as contas",
                                        ),
                                    ],
                                    width=12,
                                    md=2,
                                    className="mb-2",
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Categoria", className="fw-bold small"),
                                        dbc.Select(
                                            id="extrato-filter-category",
                                            options=[],
                                            placeholder="Todas",
                                        ),
                                    ],
                                    width=12,
                                    md=2,
                                    className="mb-2",
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Tipo", className="fw-bold small"),
                                        dbc.Select(
                                            id="extrato-filter-type",
                                            options=[
                                                {"label": "Todos", "value": "ALL"},
                                                {"label": "Receitas", "value": "INCOME"},
                                                {"label": "Despesas", "value": "EXPENSE"},
                                                {"label": "Transferências", "value": "TRANSFER"},
                                            ],
                                            value="ALL",
                                        ),
                                    ],
                                    width=6,
                                    md=1,
                                    className="mb-2",
                                ),
                                dbc.Col(
                                    [
                                        dbc.Label("Status", className="fw-bold small"),
                                        dbc.Select(
                                            id="extrato-filter-status",
                                            options=[
                                                {"label": "Todos", "value": "ALL"},
                                                {"label": "Pagos", "value": "PAID"},
                                                {"label": "Pendentes", "value": "PENDING"},
                                                {"label": "Atrasados", "value": "OVERDUE"},
                                            ],
                                            value="ALL",
                                        ),
                                    ],
                                    width=6,
                                    md=1,
                                    className="mb-2",
                                ),
                            ]
                        ),
                    ]
                ),
            ],
            className="shadow-sm border-0 mb-3",
        ),
        # Cards resumo
        dbc.Row(id="extrato-summary-cards", className="mb-3 g-3"),
        # Tabela
        dbc.Card(
            [
                dbc.CardBody(
                    [
                        # Contador de resultados + botao limpar filtros
                        dbc.Row(
                            [
                                dbc.Col(
                                    html.Div(
                                        id="extrato-result-count", className="text-muted small"
                                    ),
                                    width=8,
                                ),
                                dbc.Col(
                                    [
                                        dbc.Button(
                                            [
                                                html.I(className="bi bi-filetype-csv me-1"),
                                                "Exportar CSV",
                                            ],
                                            id="btn-export-csv",
                                            size="sm",
                                            color="primary",
                                            outline=True,
                                            className="me-2",
                                        ),
                                        dbc.Button(
                                            [
                                                html.I(className="bi bi-x-circle me-1"),
                                                "Limpar filtros",
                                            ],
                                            id="extrato-btn-clear",
                                            size="sm",
                                            color="secondary",
                                            outline=True,
                                        ),
                                    ],
                                    width=4,
                                    className="text-end",
                                ),
                            ],
                            className="mb-2",
                        ),
                        dcc.Loading(html.Div(id="extrato-table-container")),
                        # Paginacao
                        html.Div(
                            id="extrato-pagination", className="d-flex justify-content-center mt-3"
                        ),
                    ]
                )
            ],
            className="shadow-sm border-0 mb-5",
        ),
        # Modal confirmacao exclusao
        dbc.Modal(
            [
                dbc.ModalHeader(
                    dbc.ModalTitle(
                        [
                            html.I(className="bi bi-exclamation-triangle-fill text-danger me-2"),
                            "Excluir Lancamento",
                        ]
                    ),
                    close_button=True,
                ),
                dbc.ModalBody("Tem certeza? Esta acao nao pode ser desfeita."),
                dbc.ModalFooter(
                    [
                        dbc.Button(
                            "Cancelar",
                            id="extrato-btn-cancel-del",
                            color="secondary",
                            outline=True,
                            className="me-2",
                        ),
                        dbc.Button(
                            [html.I(className="bi bi-trash me-1"), "Excluir"],
                            id="extrato-btn-confirm-del",
                            color="danger",
                        ),
                    ]
                ),
            ],
            id="extrato-modal-del",
            is_open=False,
            centered=True,
        ),
        # Toast feedback
        dbc.Toast(
            id="extrato-toast",
            header="",
            is_open=False,
            dismissable=True,
            duration=3500,
            icon="success",
            style={
                "position": "fixed",
                "bottom": 24,
                "right": 24,
                "zIndex": 9999,
                "minWidth": "280px",
            },
        ),
    ],
    fluid=True,
    className="bg-light min-vh-100 py-3",
)
