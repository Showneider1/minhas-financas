import dash_bootstrap_components as dbc
from dash import html, dcc

# ===============================
# SIDEBAR (Menu Lateral)
# ===============================
sidebar = html.Div(
    [
        html.Div(
            [
                # Logo / Título
                html.H2("Finanças", className="display-6 text-primary fw-bold text-center"),
                html.Hr(),
                html.P(
                    "Controle Financeiro", className="lead fs-6 text-center text-muted"
                ),
            ],
            className="sidebar-header mb-4",
        ),
        
        # Navegação
        dbc.Nav(
            [
                dbc.NavLink(
                    [html.I(className="bi bi-speedometer2 me-2"), "Dashboard"], 
                    href="/dashboard", 
                    active="exact"
                ),
                dbc.NavLink(
                    [html.I(className="bi bi-bank me-2"), "Extrato"], 
                    href="/extrato", 
                    active="exact"
                ),
                dbc.NavLink(
                    [html.I(className="bi bi-file-earmark-bar-graph me-2"), "Relatórios"], 
                    href="/relatorios", 
                    active="exact"
                ),
                dbc.NavLink(
                    [html.I(className="bi bi-gear me-2"), "Configurações"], 
                    href="/configuracoes", 
                    active="exact"
                ),
            ],
            vertical=True,
            pills=True,
            className="flex-column flex-grow-1",
        ),
        
        # User Profile no rodapé
        html.Div([
            html.Hr(),
            dbc.Row([
                dbc.Col(
                    html.I(className="bi bi-person-circle fs-2 text-secondary"), 
                    width="auto"
                ),
                dbc.Col([
                    html.H6("Usuário", id="sidebar-user-name", className="mb-0"),
                    html.Small("email@demo.com", id="sidebar-user-email", className="text-muted text-truncate")
                ])
            ], className="align-items-center mb-2"),
            
            # Botão Novo Lançamento
            dbc.Button(
                [html.I(className="bi bi-plus-circle me-2"), "Novo Lançamento"],
                color="primary",
                id="btn-novo-lancamento",
                className="w-100 mb-2"
            ),
            
            # Botão Logout
            dbc.Button(
                "Sair",
                color="light",
                href="/logout",
                id="btn-logout",
                className="w-100 btn-sm text-danger"
            )
        ], className="mt-auto")
    ],
    className="sidebar d-flex flex-column h-100",
)

# ===============================
# MODAL DE NOVO LANÇAMENTO (Atualizado)
# ===============================
modal_novo_lancamento = dbc.Modal(
    [
        dbc.ModalHeader(
            dbc.ModalTitle("Novo Lançamento", id="modal-header-title")
        ),
        dbc.ModalBody(
            [
                # Linha 1: Tipo e Valor
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Tipo"),
                                dbc.RadioItems(
                                    options=[
                                        {"label": "Receita", "value": "INCOME"},
                                        {"label": "Despesa", "value": "EXPENSE"},
                                    ],
                                    value="EXPENSE",
                                    id="tipo-lancamento",
                                    inline=True,
                                ),
                            ],
                            width=6,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Valor (R$)"),
                                dbc.Input(
                                    id="input-valor", 
                                    placeholder="0,00", 
                                    type="text",
                                    className="form-control-lg text-end"
                                ),
                            ],
                            width=6,
                        ),
                    ],
                    className="mb-3",
                ),
                
                # Linha 2: Descrição
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Descrição"),
                                dbc.Input(id="input-descricao", placeholder="Ex: Mercado, Assinatura..."),
                            ],
                            width=12,
                        ),
                    ],
                    className="mb-3",
                ),
                
                # Linha 3: Categoria e Conta
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Categoria"),
                                dbc.Select(id="select-categoria", placeholder="Selecione..."),
                            ],
                            width=6,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Conta / Cartão"),
                                dbc.Select(id="select-conta", placeholder="Selecione..."),
                            ],
                            width=6,
                        ),
                    ],
                    className="mb-3",
                ),
                
                html.Hr(),
                html.H6("Datas e Prazos", className="text-muted mb-3"),
                
                # Linha 4: Datas (Compra e Vencimento)
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Data Compra"),
                                dcc.DatePickerSingle(
                                    id="data-compra",
                                    display_format="DD/MM/YYYY",
                                    className="d-block",
                                    style={"width": "100%"}
                                ),
                            ],
                            width=6,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Vencimento"),
                                dcc.DatePickerSingle(
                                    id="data-vencimento",
                                    display_format="DD/MM/YYYY",
                                    className="d-block",
                                    style={"width": "100%"}
                                ),
                            ],
                            width=6,
                        ),
                    ],
                    className="mb-3",
                ),
                
                # Linha 5: Status de Pagamento
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Está Pago?"),
                                dbc.Switch(
                                    id="switch-pago",
                                    label="Não / Sim",
                                    value=True, # Default: Pago (dinheiro saiu na hora)
                                    className="fs-5"
                                ),
                            ],
                            width=6,
                            className="d-flex align-items-center"
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Data do Pagamento", id="label-data-pagamento"),
                                dcc.DatePickerSingle(
                                    id="data-pagamento",
                                    display_format="DD/MM/YYYY",
                                    className="d-block",
                                    style={"width": "100%"},
                                    disabled=False
                                ),
                            ],
                            width=6,
                        ),
                    ],
                    className="mb-3",
                ),

                html.Hr(),
                
                # Linha 6: Recorrência e Parcelas
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Recorrência / Parcelas"),
                        dbc.Checklist(
                            options=[
                                {"label": "É Assinatura Fixa?", "value": "recorrente"},
                            ],
                            value=[],
                            id="check-recorrencia",
                            switch=True,
                        ),
                    ], width=4),
                    
                    dbc.Col([
                        dbc.Label("Parcela Atual"),
                        dbc.Input(id="input-parcela-atual", type="number", value=1, min=1),
                    ], width=4),
                    
                    dbc.Col([
                        dbc.Label("Total Parcelas"),
                        dbc.Input(id="input-total-parcelas", type="number", value=1, min=1),
                    ], width=4),
                ], className="mb-3"),

                html.Div(id="feedback-transacao"),
            ]
        ),
        dbc.ModalFooter(
            [
                dbc.Button(
                    "Cancelar", id="btn-cancelar-modal", className="ms-auto", n_clicks=0
                ),
                dbc.Button(
                    "Salvar Lançamento", id="btn-salvar-lancamento", color="primary", n_clicks=0
                ),
            ]
        ),
    ],
    id="modal-novo-lancamento",
    is_open=False,
    size="lg",
)