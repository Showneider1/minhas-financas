"""
Modal para novo lançamento de transações.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc
from datetime import date


def create_transaction_modal():
    """
    Cria o modal de novo lançamento.
    """
    return dbc.Modal(
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
        is_open=False,  # ← IMPORTANTE: Começa fechado
        backdrop="static",
        size="lg",
    )
