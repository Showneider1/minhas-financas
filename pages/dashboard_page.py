"""
Página principal - Dashboard.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc
from datetime import date

def layout():
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.H2("Dashboard", className="mb-0 fw-bold"),
                html.P("Visão geral das suas finanças", className="text-muted"),
            ]),
        ], className="mb-4"),
        
        # Filtros
        dbc.Row([
            dbc.Col([
                dbc.Label("Período:", className="fw-bold me-2"),
                dcc.DatePickerRange(
                    id="dashboard-periodo",
                    display_format="DD/MM/YYYY",
                    start_date=date.today().replace(day=1),
                    end_date=date.today(),
                ),
            ], width=6),
            dbc.Col([
                dbc.Button(
                    [html.I(className="bi bi-download me-2"), "Exportar"],
                    id="btn-export-dashboard",
                    color="primary",
                    outline=True,
                ),
            ], width=6, className="text-end"),
        ], className="mb-4"),
        
        # KPIs
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Saldo", className="text-muted mb-2"),
                        html.H3(id="kpi-saldo", children="R$ 0,00", className="fw-bold mb-1"),
                        html.Small(id="kpi-saldo-variacao", className="text-success"),
                    ])
                ], className="shadow-sm border-0"),
            ], width=12, md=4, className="mb-3"),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Receitas", className="text-muted mb-2"),
                        html.H3(id="kpi-receita", children="R$ 0,00", className="fw-bold mb-1 text-success"),
                        html.Small(id="kpi-receita-variacao", className="text-muted"),
                    ])
                ], className="shadow-sm border-0"),
            ], width=12, md=4, className="mb-3"),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Despesas", className="text-muted mb-2"),
                        html.H3(id="kpi-despesa", children="R$ 0,00", className="fw-bold mb-1 text-danger"),
                        html.Small(id="kpi-despesa-variacao", className="text-muted"),
                    ])
                ], className="shadow-sm border-0"),
            ], width=12, md=4, className="mb-3"),
        ]),
        
        # Gráficos
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Evolução Mensal"),
                    dbc.CardBody([
                        dcc.Graph(id="grafico-fluxo-caixa"),
                    ]),
                ], className="shadow-sm border-0"),
            ], width=12, lg=8, className="mb-3"),
            
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Por Categoria"),
                    dbc.CardBody([
                        dcc.Graph(id="grafico-categorias"),
                    ]),
                ], className="shadow-sm border-0"),
            ], width=12, lg=4, className="mb-3"),
        ]),
        
    ], fluid=True, className="py-4")
