"""
Página de configurações - Categorias e Contas.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc

layout = dbc.Container([
    # Header
    dbc.Row([
        dbc.Col([
            html.H2("Configurações", className="mb-0 fw-bold"),
            html.P("Gerencie suas categorias e contas", className="text-muted"),
        ]),
    ], className="mb-4"),
    
    # Tabs
    dbc.Tabs([
        # ABA CATEGORIAS
        dbc.Tab(
            label="📁 Categorias",
            tab_id="tab-categorias",
            children=[
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            [html.I(className="bi bi-plus-circle me-2"), "Nova Categoria"],
                            id="btn-nova-categoria",
                            color="primary",
                            className="mt-3 mb-3",
                        ),
                    ]),
                ]),
                
                # Feedback
                html.Div(id="feedback-categorias"),
                
                # Lista de categorias
                html.Div(id="lista-categorias"),
            ],
        ),
        
        # ABA CONTAS
        dbc.Tab(
            label="🏦 Contas",
            tab_id="tab-contas",
            children=[
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            [html.I(className="bi bi-plus-circle me-2"), "Nova Conta"],
                            id="btn-nova-conta",
                            color="primary",
                            className="mt-3 mb-3",
                        ),
                    ]),
                ]),
                
                # Feedback
                html.Div(id="feedback-contas"),
                
                # Lista de contas
                html.Div(id="lista-contas"),
            ],
        ),
    ], id="tabs-configuracoes", active_tab="tab-categorias"),
    
    # MODAL NOVA CATEGORIA
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Nova Categoria")),
        dbc.ModalBody([
            html.Div(id="feedback-modal-categoria"),
            
            dbc.Label("Nome da Categoria", className="fw-bold"),
            dbc.Input(
                id="input-categoria-nome",
                placeholder="Ex: Alimentação, Transporte, Moradia...",
                className="mb-3",
            ),
            
            dbc.Label("Categoria Principal (opcional)", className="fw-bold"),
            dbc.Select(
                id="select-categoria-pai",
                options=[{"label": "Nenhuma (criar categoria principal)", "value": ""}],
                className="mb-3",
            ),
            
            html.Small("💡 Deixe em branco para criar uma categoria principal, ou selecione uma categoria existente para criar uma subcategoria.", className="text-muted"),
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancelar", id="btn-cancelar-categoria", color="secondary", outline=True),
            dbc.Button("Salvar", id="btn-salvar-categoria", color="primary"),
        ]),
    ], id="modal-categoria", is_open=False, size="md"),
    
    # MODAL NOVA CONTA
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Nova Conta")),
        dbc.ModalBody([
            html.Div(id="feedback-modal-conta"),
            
            dbc.Label("Nome", className="fw-bold"),
            dbc.Input(
                id="input-conta-nome",
                placeholder="Ex: Banco Itaú",
                className="mb-3",
            ),
            
            dbc.Label("Tipo", className="fw-bold"),
            dbc.Select(
                id="input-conta-tipo",
                options=[
                    {"label": "Conta Corrente", "value": "CHECKING"},
                    {"label": "Poupança", "value": "SAVINGS"},
                    {"label": "Cartão de Crédito", "value": "CREDIT_CARD"},
                    {"label": "Dinheiro", "value": "CASH"},
                    {"label": "Investimentos", "value": "INVESTMENT"},
                ],
                value="CHECKING",
                className="mb-3",
            ),
            
            dbc.Label("Saldo Inicial", className="fw-bold"),
            dbc.Input(
                id="input-conta-saldo",
                type="text",
                placeholder="R$ 0,00",
                value="0",
                className="mb-3",
            ),
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancelar", id="btn-cancelar-conta", color="secondary", outline=True),
            dbc.Button("Salvar", id="btn-salvar-conta", color="primary"),
        ]),
    ], id="modal-conta", is_open=False, size="md"),
    
], fluid=True, className="py-4")
