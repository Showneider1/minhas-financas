"""
Página de relatórios.
"""
import dash_bootstrap_components as dbc
from dash import html

layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H2("Relatórios", className="fw-bold"),
            html.P("Em desenvolvimento...", className="text-muted"),
        ]),
    ]),
], fluid=True, className="py-4")
