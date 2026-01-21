"""
Página de Extrato de Lançamentos.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc
from datetime import date

layout = dbc.Container([
    # Store para recarregar dados
    dcc.Store(id="extrato-reload-trigger", data=0),

    # Título
    dbc.Row([
        dbc.Col([
            html.H2("Extrato de Lançamentos", className="fw-bold text-primary"),
            html.P("Consulte e gerencie todo o seu histórico financeiro.", className="text-muted"),
        ], width=12, md=8),
        dbc.Col([
            dbc.Button(
                [html.I(className="bi bi-plus-lg me-2"), "Novo Lançamento"],
                id="btn-novo-lancamento-extrato", # Conectar ao modal global se desejar
                color="success",
                className="mt-2 w-100"
            )
        ], width=12, md=4, className="text-end"),
    ], className="mb-4 mt-3"),

    # Barra de Filtros (Card)
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                # Filtro Data
                dbc.Col([
                    dbc.Label("Período", className="fw-bold small"),
                    dcc.DatePickerRange(
                        id="extrato-filter-date",
                        display_format="DD/MM/YYYY",
                        start_date=date.today().replace(day=1),
                        end_date=date.today(),
                        className="w-100" # Classe CSS para ajustar largura se possível
                    ),
                ], width=12, md=4, className="mb-3"),

                # Filtro Conta
                dbc.Col([
                    dbc.Label("Conta Bancária", className="fw-bold small"),
                    dbc.Select(id="extrato-filter-account", options=[], placeholder="Todas as contas"),
                ], width=12, md=2, className="mb-3"),

                # Filtro Categoria
                dbc.Col([
                    dbc.Label("Categoria", className="fw-bold small"),
                    dbc.Select(id="extrato-filter-category", options=[], placeholder="Todas"),
                ], width=12, md=2, className="mb-3"),

                # Filtro Tipo
                dbc.Col([
                    dbc.Label("Tipo", className="fw-bold small"),
                    dbc.Select(
                        id="extrato-filter-type",
                        options=[
                            {"label": "Todas", "value": "ALL"},
                            {"label": "Receitas", "value": "INCOME"},
                            {"label": "Despesas", "value": "EXPENSE"},
                        ],
                        value="ALL"
                    ),
                ], width=12, md=2, className="mb-3"),

                # Filtro Status
                dbc.Col([
                    dbc.Label("Status", className="fw-bold small"),
                    dbc.Select(
                        id="extrato-filter-status",
                        options=[
                            {"label": "Todos", "value": "ALL"},
                            {"label": "Pagos", "value": "PAID"},
                            {"label": "Pendentes", "value": "PENDING"},
                        ],
                        value="ALL"
                    ),
                ], width=12, md=2, className="mb-3"),
            ])
        ])
    ], className="shadow-sm border-0 mb-4"),

    # Resumo Rápido (Cards pequenos acima da tabela)
    dbc.Row(id="extrato-summary-cards", className="mb-4"),

    # Tabela de Resultados
    dbc.Card([
        dbc.CardBody([
            dcc.Loading(
                html.Div(id="extrato-table-container")
            )
        ])
    ], className="shadow-sm border-0 mb-5")

], fluid=True, className="bg-light min-vh-100 py-3")