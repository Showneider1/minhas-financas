"""
Sidebar de navegação da aplicação.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc
from datetime import date

# ===============================
# SIDEBAR
# ===============================
sidebar = html.Div(
    [
        # Logo e Nome
        html.Div(
            [
                html.I(className="bi bi-wallet2 fs-2 text-primary mb-2"),
                html.H4("Finanças", className="mb-0 fw-bold"),
                html.Small("Sistema Financeiro", className="text-muted"),
            ],
            className="text-center py-4 border-bottom",
        ),
        
        # Informações do Usuário
        html.Div(
            [
                html.Div(
                    [
                        html.I(className="bi bi-person-circle fs-3 text-secondary"),
                    ],
                    className="text-center mb-2",
                ),
                html.P(
                    id="sidebar-user-name",
                    children="Usuário",
                    className="mb-0 fw-bold small text-center",
                ),
                html.P(
                    id="sidebar-user-email",
                    children="email@exemplo.com",
                    className="text-muted small text-center",
                ),
            ],
            className="px-3 py-3 border-bottom",
        ),
        
        # Botão Novo Lançamento
        html.Div(
            dbc.Button(
                [
                    html.I(className="bi bi-plus-circle me-2"),
                    "Novo Lançamento"
                ],
                id="btn-novo-lancamento",
                color="primary",
                className="w-100",
                size="lg",
                n_clicks=0,
            ),
            className="p-3",
        ),
        
        # Menu de Navegação
        dbc.Nav(
            [
                dbc.NavLink(
                    [
                        html.I(className="bi bi-speedometer2 me-2"),
                        "Dashboard"
                    ],
                    href="/dashboard",
                    active="exact",
                    className="text-dark",
                ),
                dbc.NavLink(
                    [
                        html.I(className="bi bi-list-ul me-2"),
                        "Extrato"
                    ],
                    href="/extrato",
                    active="exact",
                    className="text-dark",
                ),
                dbc.NavLink(
                    [
                        html.I(className="bi bi-file-earmark-bar-graph me-2"),
                        "Relatórios"
                    ],
                    href="/relatorios",
                    active="exact",
                    className="text-dark",
                ),
                dbc.NavLink(
                    [
                        html.I(className="bi bi-gear me-2"),
                        "Configurações"
                    ],
                    href="/configuracoes",
                    active="exact",
                    className="text-dark",
                ),
            ],
            vertical=True,
            pills=True,
            className="px-3",
        ),
        
        # Botão Logout (no final)
        html.Div(
            dbc.Button(
                [
                    html.I(className="bi bi-box-arrow-right me-2"),
                    "Sair"
                ],
                id="btn-logout",
                color="danger",
                outline=True,
                className="w-100",
                n_clicks=0,
            ),
            className="p-3 mt-auto border-top",
        ),
    ],
    style={
        "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "280px",
        "backgroundColor": "#f8f9fa",
        "overflowY": "auto",
        "display": "flex",
        "flexDirection": "column",
    },
)

# ===============================
# MODAL NOVO LANÇAMENTO
# ===============================
modal_novo_lancamento = dbc.Modal(
    [
        dbc.ModalHeader(
            dbc.ModalTitle("Novo Lançamento"),
            close_button=True,
        ),
        dbc.ModalBody([
            # Feedback de erro/sucesso
            html.Div(id="feedback-transacao"),
            
            # Formulário
            dbc.Form([
                # Tipo de lançamento
                dbc.Label("Tipo", className="fw-bold"),
                dbc.RadioItems(
                    id="tipo-lancamento",
                    options=[
                        {"label": "💰 Receita", "value": "INCOME"},
                        {"label": "💸 Despesa", "value": "EXPENSE"},
                    ],
                    value="EXPENSE",
                    inline=True,
                    className="mb-3",
                ),
                
                # Valor
                dbc.Label("Valor", className="fw-bold"),
                dbc.Input(
                    id="input-valor",
                    type="text",
                    placeholder="R$ 0,00",
                    className="mb-3",
                ),
                
                # Descrição
                dbc.Label("Descrição", className="fw-bold"),
                dbc.Input(
                    id="input-descricao",
                    type="text",
                    placeholder="Ex: Supermercado",
                    className="mb-3",
                ),
                
                # Categoria
                dbc.Label("Categoria", className="fw-bold"),
                dbc.Select(
                    id="select-categoria",
                    placeholder="Selecione a categoria",
                    className="mb-3",
                ),
                
                # Conta
                dbc.Label("Conta", className="fw-bold"),
                dbc.Select(
                    id="select-conta",
                    placeholder="Selecione a conta",
                    className="mb-3",
                ),
                
                # Data
                dbc.Label("Data", className="fw-bold"),
                dcc.DatePickerSingle(
                    id="data-lancamento",
                    display_format="DD/MM/YYYY",
                    date=date.today(),
                    className="mb-3",
                ),
                
                # Já foi pago?
                dbc.Checkbox(
                    id="switch-pago",
                    label="Já foi pago",
                    value=False,
                    className="mb-3",
                ),
            ]),
        ]),
        dbc.ModalFooter([
            dbc.Button(
                "Cancelar",
                id="btn-cancelar-modal",
                color="secondary",
                outline=True,
                className="me-2",
                n_clicks=0,
            ),
            dbc.Button(
                "Salvar",
                id="btn-salvar-lancamento",
                color="primary",
                n_clicks=0,
            ),
        ]),
    ],
    id="modal-novo-lancamento",
    is_open=False,
    backdrop="static",
    size="lg",
)
