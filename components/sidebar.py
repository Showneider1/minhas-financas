"""
Sidebar e Modal de Novo Lançamento (Layout Melhorado).
"""

import dash_bootstrap_components as dbc
from dash import html

from components.transaction_modal import create_transaction_modal

# ===============================
# SIDEBAR (Menu Lateral)
# ===============================
sidebar = html.Div(
    [
        # ---- LOGO / MARCA ----
        html.Div(
            [
                html.Div(
                    [
                        html.I(className="bi bi-cash-stack fs-3 text-white me-2"),
                        html.Span("Finanças", className="fw-bold text-white fs-4"),
                    ],
                    className="d-flex align-items-center justify-content-center py-2",
                ),
                html.P(
                    "Controle Financeiro",
                    className="text-center mb-0",
                    style={
                        "color": "rgba(255,255,255,0.6)",
                        "fontSize": "0.75rem",
                        "letterSpacing": "0.08em",
                    },
                ),
            ],
            className="sidebar-header py-3 px-3 mb-2",
            style={
                "background": "rgba(255,255,255,0.05)",
                "borderRadius": "10px",
                "margin": "0 8px",
            },
        ),
        html.Div(
            style={"height": "1px", "background": "rgba(255,255,255,0.1)", "margin": "12px 16px"}
        ),
        # ---- NAVEGAÇÃO ----
        dbc.Nav(
            [
                dbc.NavLink(
                    [html.I(className="bi bi-speedometer2 me-2"), "Dashboard"],
                    href="/dashboard",
                    active="exact",
                    className="sidebar-link",
                ),
                dbc.NavLink(
                    [html.I(className="bi bi-bank me-2"), "Extrato"],
                    href="/extrato",
                    active="exact",
                    className="sidebar-link",
                ),
                dbc.NavLink(
                    [html.I(className="bi bi-flag-fill me-2"), "Metas"],
                    href="/metas",
                    active="exact",
                    className="sidebar-link",
                ),
                dbc.NavLink(
                    [html.I(className="bi bi-graph-up-arrow me-2"), "Investimentos"],
                    href="/investimentos",
                    active="exact",
                    className="sidebar-link",
                ),
                dbc.NavLink(
                    [html.I(className="bi bi-repeat me-2"), "Recorrências"],
                    href="/recorrencia",
                    active="exact",
                    className="sidebar-link",
                ),
                dbc.NavLink(
                    [html.I(className="bi bi-credit-card me-2"), "Cartões"],
                    href="/cartoes",
                    active="exact",
                    className="sidebar-link",
                ),
                dbc.NavLink(
                    [html.I(className="bi bi-graph-up-arrow me-2"), "Analytics"],
                    href="/analytics",
                    active="exact",
                    className="sidebar-link",
                ),
                dbc.NavLink(
                    [html.I(className="bi bi-cloud-arrow-up me-2"), "Importação"],
                    href="/importacao",
                    active="exact",
                    className="sidebar-link",
                ),
                dbc.NavLink(
                    [html.I(className="bi bi-file-earmark-bar-graph me-2"), "Relatórios"],
                    href="/relatorios",
                    active="exact",
                    className="sidebar-link",
                ),
                dbc.NavLink(
                    [html.I(className="bi bi-gear me-2"), "Configurações"],
                    href="/configuracoes",
                    active="exact",
                    className="sidebar-link",
                ),
            ],
            vertical=True,
            pills=True,
            className="flex-column flex-grow-1 px-2",
        ),
        # ---- RODAPÉ: USUÁRIO + AÇÕES ----
        html.Div(
            [
                html.Div(
                    style={
                        "height": "1px",
                        "background": "rgba(255,255,255,0.1)",
                        "marginBottom": "12px",
                    }
                ),
                # Info do usuário (carregada dinamicamente pelo callback)
                dbc.Row(
                    [
                        dbc.Col(
                            html.Div(
                                html.I(className="bi bi-person-circle fs-4 text-white"),
                                style={
                                    "width": "38px",
                                    "height": "38px",
                                    "background": "rgba(255,255,255,0.15)",
                                    "borderRadius": "50%",
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": "center",
                                },
                            ),
                            width="auto",
                        ),
                        dbc.Col(
                            [
                                html.Div(
                                    id="sidebar-user-name",
                                    children="Usuário",
                                    className="fw-bold text-white mb-0",
                                    style={"fontSize": "0.85rem", "lineHeight": "1.2"},
                                ),
                                html.Div(
                                    id="sidebar-user-email",
                                    children="...",
                                    className="text-truncate",
                                    style={
                                        "color": "rgba(255,255,255,0.55)",
                                        "fontSize": "0.72rem",
                                    },
                                ),
                            ]
                        ),
                    ],
                    className="align-items-center g-2 mb-3 px-1",
                ),
                # Botão Novo Lançamento
                dbc.Button(
                    [html.I(className="bi bi-plus-circle-fill me-2"), "Novo Lançamento"],
                    color="light",
                    id="btn-novo-lancamento",
                    className="w-100 mb-2 fw-bold",
                    style={"color": "#0d6efd", "borderRadius": "8px"},
                ),
                # Botão Sair
                dbc.Button(
                    [html.I(className="bi bi-box-arrow-left me-2"), "Sair"],
                    color="link",
                    href="/logout",
                    id="btn-logout",
                    className="w-100 btn-sm text-danger p-1",
                    style={"fontSize": "0.82rem"},
                ),
            ],
            className="mt-auto px-2 pb-2",
        ),
    ],
    className="sidebar d-flex flex-column",
    style={
        "position": "fixed",
        "top": 0,
        "left": 0,
        "width": "240px",
        "height": "100vh",
        "background": "linear-gradient(180deg, #1a2a4a 0%, #1e3a5f 100%)",
        "boxShadow": "3px 0 15px rgba(0,0,0,0.15)",
        "overflowY": "auto",
        "zIndex": 1000,
        "padding": "12px 4px",
    },
)

modal_novo_lancamento = create_transaction_modal()
