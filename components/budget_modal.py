import dash_bootstrap_components as dbc
from dash import html, dcc

modal_budget = dbc.Modal(
    [
        dbc.ModalHeader(dbc.ModalTitle("Definir Meta de Gastos")),
        dbc.ModalBody([
            html.Div(id="budget-feedback"),
            
            dbc.Label("Categoria", className="fw-bold"),
            dbc.Select(
                id="select-budget-category",
                placeholder="Selecione a categoria...",
                className="mb-3"
            ),
            
            dbc.Label("Valor Limite Mensal", className="fw-bold"),
            dbc.Input(
                id="input-budget-amount",
                type="number",
                placeholder="Ex: 500.00",
                className="mb-3"
            ),
        ]),
        dbc.ModalFooter([
            dbc.Button("Salvar Meta", id="btn-save-budget", color="primary", n_clicks=0),
            dbc.Button("Fechar", id="btn-close-budget", color="secondary", n_clicks=0),
        ]),
    ],
    id="modal-budget",
    is_open=False,
    size="md",
)