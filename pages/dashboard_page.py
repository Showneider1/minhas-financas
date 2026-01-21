"""
Página principal - Dashboard.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc
from datetime import date

layout = dbc.Container([
    # Store para trigger de reload
    dcc.Store(id="store-reload-dashboard", data=0),
    
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
                className="ms-2"
            ),
        ], width=12, md=6, className="d-flex align-items-center mb-3"),
        
        dbc.Col([
            dbc.Button(
                [html.I(className="bi bi-arrow-repeat me-2"), "Atualizar"],
                id="btn-update-dashboard",
                color="secondary",
                outline=True,
                className="me-2"
            ),
        ], width=12, md=6, className="text-md-end mb-3"),
    ], className="mb-4"),
    
    # KPIs
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Saldo em Caixa", className="text-muted mb-2"),
                    html.H3(id="kpi-saldo", children="R$ ...", className="fw-bold mb-1 text-primary"),
                    html.Small("Saldo total acumulado", className="text-muted"),
                ])
            ], className="shadow-sm border-0 h-100"),
        ], width=12, md=4, className="mb-3"),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Receitas (Período)", className="text-muted mb-2"),
                    html.H3(id="kpi-receita", children="R$ ...", className="fw-bold mb-1 text-success"),
                    html.Small(id="kpi-receita-info", className="text-muted"),
                ])
            ], className="shadow-sm border-0 h-100"),
        ], width=12, md=4, className="mb-3"),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Despesas (Período)", className="text-muted mb-2"),
                    html.H3(id="kpi-despesa", children="R$ ...", className="fw-bold mb-1 text-danger"),
                    html.Small(id="kpi-despesa-info", className="text-muted"),
                ])
            ], className="shadow-sm border-0 h-100"),
        ], width=12, md=4, className="mb-3"),
    ]),
    
    # LINHA PRINCIPAL: Gráfico de Evolução + Tabela de Vencimentos
    dbc.Row([
        # Gráfico Fluxo de Caixa (Largo)
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Fluxo de Caixa Mensal", className="bg-white fw-bold"),
                dbc.CardBody([
                    dcc.Loading(
                        dcc.Graph(id="grafico-fluxo-caixa", config={"displayModeBar": False}, style={"height": "300px"})
                    ),
                ]),
            ], className="shadow-sm border-0 h-100"),
        ], width=12, lg=7, className="mb-3"),
        
        # Tabela Próximos Vencimentos (Lateral)
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.I(className="bi bi-calendar-event me-2 text-warning"),
                    "Próximos Vencimentos"
                ], className="bg-white fw-bold"),
                
                dbc.CardBody([
                    dcc.Loading(
                        html.Div(id="tabela-proximos-vencimentos")
                    )
                ], style={"overflowY": "auto", "maxHeight": "340px"}),
            ], className="shadow-sm border-0 h-100"),
        ], width=12, lg=5, className="mb-3"),
    ]),
    
    # LINHA SECUNDÁRIA: Gráfico de Categorias
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Despesas por Categoria", className="bg-white fw-bold"),
                dbc.CardBody([
                    dcc.Loading(
                        dcc.Graph(id="grafico-categorias", config={"displayModeBar": False}, style={"height": "300px"})
                    ),
                ]),
            ], className="shadow-sm border-0 h-100"),
        ], width=12, className="mb-3"),
    ]),
    
], fluid=True, className="py-4")