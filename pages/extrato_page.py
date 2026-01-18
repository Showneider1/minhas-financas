"""
Página de extrato de transações.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc
from datetime import date

layout = dbc.Container([
    dcc.Store(id="store-reload-dashboard", data=0),
    # Header
    dbc.Row([
        dbc.Col([
            html.H2("Extrato", className="mb-0 fw-bold"),
            html.P("Histórico de transações", className="text-muted"),
        ]),
    ], className="mb-4"),
    
    # Filtros
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Input(
                        id="busca-extrato",
                        placeholder="Buscar transações...",
                        type="text",
                    ),
                ], width=12, md=4, className="mb-3"),
                
                dbc.Col([
                    dcc.DatePickerRange(
                        id="extrato-periodo",
                        display_format="DD/MM/YYYY",
                        start_date=date.today().replace(day=1),
                        end_date=date.today(),
                    ),
                ], width=12, md=4, className="mb-3"),
                
                dbc.Col([
                    dbc.Button(
                        [html.I(className="bi bi-funnel me-2"), "Filtros"],
                        id="btn-toggle-filtros",
                        color="secondary",
                        outline=True,
                        className="me-2",
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-download me-2"), "Exportar"],
                        id="btn-export-pdf",
                        color="primary",
                        outline=True,
                    ),
                ], width=12, md=4, className="mb-3 text-end"),
            ]),
            
            # Filtros Avançados (Collapse)
            dbc.Collapse([
                html.Hr(),
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Tipo:", className="fw-bold"),
                        dbc.Checklist(
                            id="extrato-tipo",
                            options=[
                                {"label": "Receitas", "value": "INCOME"},
                                {"label": "Despesas", "value": "EXPENSE"},
                            ],
                            value=[],
                            inline=True,
                        ),
                    ], width=12, md=6, className="mb-3"),
                    
                    dbc.Col([
                        dbc.Label("Status:", className="fw-bold"),
                        dbc.Checklist(
                            id="extrato-status",
                            options=[
                                {"label": "Pago", "value": "PAID"},
                                {"label": "Pendente", "value": "PENDING"},
                            ],
                            value=[],
                            inline=True,
                        ),
                    ], width=12, md=6, className="mb-3"),
                ]),
            ], id="collapse-filtros-extrato", is_open=False),
        ]),
    ], className="mb-4 shadow-sm border-0"),
    
    # Resumo
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Entradas", className="text-muted mb-1"),
                    html.H4(id="total-entradas-extrato", className="text-success fw-bold mb-0"),
                ]),
            ], className="shadow-sm border-0"),
        ], width=12, md=4, className="mb-3"),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Saídas", className="text-muted mb-1"),
                    html.H4(id="total-saidas-extrato", className="text-danger fw-bold mb-0"),
                ]),
            ], className="shadow-sm border-0"),
        ], width=12, md=4, className="mb-3"),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Saldo do Período", className="text-muted mb-1"),
                    html.H4(id="saldo-periodo-extrato", className="fw-bold mb-0"),
                ]),
            ], className="shadow-sm border-0"),
        ], width=12, md=4, className="mb-3"),
    ]),
    
    # Lista de Transações
    html.Div(id="tabela-extrato"),
    
], fluid=True, className="py-4")
