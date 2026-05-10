"""
Sidebar e Modal de Novo Lançamento (Layout Melhorado).
"""
import dash_bootstrap_components as dbc
from dash import html, dcc

# ===============================
# SIDEBAR (Menu Lateral)
# ===============================
sidebar = html.Div(
    [
        # ---- LOGO / MARCA ----
        html.Div([
            html.Div([
                html.I(className="bi bi-cash-stack fs-3 text-white me-2"),
                html.Span("Finanças", className="fw-bold text-white fs-4"),
            ], className="d-flex align-items-center justify-content-center py-2"),
            html.P("Controle Financeiro", className="text-center mb-0",
                   style={"color": "rgba(255,255,255,0.6)", "fontSize": "0.75rem", "letterSpacing": "0.08em"}),
        ], className="sidebar-header py-3 px-3 mb-2",
           style={"background": "rgba(255,255,255,0.05)", "borderRadius": "10px", "margin": "0 8px"}),

        html.Div(style={"height": "1px", "background": "rgba(255,255,255,0.1)", "margin": "12px 16px"}),

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
        html.Div([
            html.Div(style={"height": "1px", "background": "rgba(255,255,255,0.1)", "marginBottom": "12px"}),

            # Info do usuário (carregada dinamicamente pelo callback)
            dbc.Row([
                dbc.Col(
                    html.Div(
                        html.I(className="bi bi-person-circle fs-4 text-white"),
                        style={
                            "width": "38px", "height": "38px",
                            "background": "rgba(255,255,255,0.15)",
                            "borderRadius": "50%",
                            "display": "flex", "alignItems": "center", "justifyContent": "center"
                        }
                    ),
                    width="auto"
                ),
                dbc.Col([
                    html.Div(id="sidebar-user-name", children="Usuário",
                             className="fw-bold text-white mb-0",
                             style={"fontSize": "0.85rem", "lineHeight": "1.2"}),
                    html.Div(id="sidebar-user-email", children="...",
                             className="text-truncate",
                             style={"color": "rgba(255,255,255,0.55)", "fontSize": "0.72rem"}),
                ]),
            ], className="align-items-center g-2 mb-3 px-1"),

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
        ], className="mt-auto px-2 pb-2"),
    ],
    className="sidebar d-flex flex-column",
    style={
        "position": "fixed",
        "top": 0, "left": 0,
        "width": "240px",
        "height": "100vh",
        "background": "linear-gradient(180deg, #1a2a4a 0%, #1e3a5f 100%)",
        "boxShadow": "3px 0 15px rgba(0,0,0,0.15)",
        "overflowY": "auto",
        "zIndex": 1000,
        "padding": "12px 4px",
    },
)

# ===============================
# MODAL DE NOVO LANÇAMENTO
# ===============================
modal_novo_lancamento = dbc.Modal(
    [
        dbc.ModalHeader(
            dbc.ModalTitle(
                [html.I(className="bi bi-plus-circle me-2 text-primary"),
                 html.Span("Novo Lançamento", id="modal-header-title")],
            ),
            close_button=True,
        ),
        dbc.ModalBody([

            # TIPO E VALOR
            dbc.Row([
                dbc.Col([
                    dbc.Label("Tipo", className="fw-bold"),
                    dbc.RadioItems(
                        options=[
                            {"label": html.Span([
                                html.I(className="bi bi-arrow-up-circle-fill text-success me-1"),
                                " Receita"
                            ]), "value": "INCOME"},
                            {"label": html.Span([
                                html.I(className="bi bi-arrow-down-circle-fill text-danger me-1"),
                                " Despesa"
                            ]), "value": "EXPENSE"},
                        ],
                        value="EXPENSE",
                        id="tipo-lancamento",
                        inline=True,
                        className="mt-1",
                    ),
                ], width=6),
                dbc.Col([
                    dbc.Label("Valor (R$)", className="fw-bold"),
                    dbc.InputGroup([
                        dbc.InputGroupText("R$",
                                           style={"background": "#f8f9fa", "fontWeight": "600"}),
                        dbc.Input(
                            id="input-valor",
                            placeholder="0,00",
                            type="text",
                            className="text-end fs-5 fw-bold",
                            style={"borderLeft": "none"},
                        ),
                    ]),
                ], width=6),
            ], className="mb-3"),

            # DESCRIÇÃO
            dbc.Row([
                dbc.Col([
                    dbc.Label("Descrição", className="fw-bold"),
                    dbc.Input(
                        id="input-descricao",
                        placeholder="Ex: Mercado, Salário, Aluguel...",
                        maxLength=100,
                    ),
                ]),
            ], className="mb-3"),

            # CATEGORIA E CONTA
            dbc.Row([
                dbc.Col([
                    dbc.Label("Categoria", className="fw-bold"),
                    dbc.Select(id="select-categoria", placeholder="Selecione..."),
                ], width=6),
                dbc.Col([
                    dbc.Label("Conta / Cartão", className="fw-bold"),
                    dbc.Select(id="select-conta", placeholder="Selecione..."),
                ], width=6),
            ], className="mb-3"),

            html.Hr(className="my-3"),
            html.P([
                html.I(className="bi bi-calendar3 me-2 text-muted"),
                html.Span("Datas e Prazos", className="text-muted fw-bold small text-uppercase",
                          style={"letterSpacing": "0.05em"}),
            ], className="mb-2"),

            # DATAS
            dbc.Row([
                dbc.Col([
                    dbc.Label("Data Compra", className="fw-bold small"),
                    dcc.DatePickerSingle(
                        id="data-compra",
                        display_format="DD/MM/YYYY",
                        className="d-block",
                        style={"width": "100%"},
                    ),
                ], width=4),
                dbc.Col([
                    dbc.Label("Vencimento", className="fw-bold small"),
                    dcc.DatePickerSingle(
                        id="data-vencimento",
                        display_format="DD/MM/YYYY",
                        className="d-block",
                        style={"width": "100%"},
                    ),
                ], width=4),
                dbc.Col([
                    dbc.Label("Data Pagamento", className="fw-bold small"),
                    dcc.DatePickerSingle(
                        id="data-pagamento",
                        display_format="DD/MM/YYYY",
                        className="d-block",
                        style={"width": "100%"},
                        disabled=False,
                    ),
                ], width=4),
            ], className="mb-3"),

            # STATUS PAGO
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col([
                                    html.P("Lançamento pago?", className="mb-0 fw-bold small"),
                                    html.Small("Marque se o valor já foi pago/recebido",
                                               className="text-muted"),
                                ]),
                                dbc.Col([
                                    dbc.Switch(
                                        id="switch-pago",
                                        label="",
                                        value=True,
                                        className="fs-4 mb-0",
                                    ),
                                ], width="auto", className="d-flex align-items-center"),
                            ], className="align-items-center"),
                        ], className="py-2"),
                    ], className="border-0 bg-light"),
                ], width=12),
            ], className="mb-3"),

            html.Hr(className="my-3"),
            html.P([
                html.I(className="bi bi-repeat me-2 text-muted"),
                html.Span("Recorrência e Parcelas", className="text-muted fw-bold small text-uppercase",
                          style={"letterSpacing": "0.05em"}),
            ], className="mb-2"),

            # RECORRÊNCIA E PARCELAS
            dbc.Row([
                dbc.Col([
                    dbc.Checklist(
                        options=[{"label": " É assinatura/despesa fixa?", "value": "recorrente"}],
                        value=[],
                        id="check-recorrencia",
                        switch=True,
                    ),
                ], width=12, md=4),
                dbc.Col([
                    dbc.Label("Parcela Atual", className="fw-bold small"),
                    dbc.Input(id="input-parcela-atual", type="number", value=1, min=1),
                ], width=6, md=4),
                dbc.Col([
                    dbc.Label("Total de Parcelas", className="fw-bold small"),
                    dbc.Input(id="input-total-parcelas", type="number", value=1, min=1),
                ], width=6, md=4),
            ], className="mb-3"),

            # FEEDBACK
            html.Div(id="feedback-transacao"),

        ]),
        dbc.ModalFooter([
            dbc.Button(
                [html.I(className="bi bi-x me-1"), "Cancelar"],
                id="btn-cancelar-modal",
                color="secondary",
                outline=True,
                n_clicks=0,
            ),
            dbc.Button(
                [html.I(className="bi bi-check2 me-1"), "Salvar Lançamento"],
                id="btn-salvar-lancamento",
                color="primary",
                n_clicks=0,
            ),
        ]),
    ],
    id="modal-novo-lancamento",
    is_open=False,
    size="lg",
    backdrop="static",
)
