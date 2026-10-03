"""
Página de Caixinhas (Virtual Vaults/Envelopes).
Interface com Cards progressivos e modais para guardar/resgatar.
"""

import dash_bootstrap_components as dbc
from dash import dcc, html


# Modal genérico para alocar ou resgar fundos
modal_vault = dbc.Modal(
    [
        dbc.ModalHeader(
            dbc.ModalTitle("Gerenciar Caixinha - vault-modal-title"),
            close_button=True,
        ),
        dbc.ModalBody([
            dbc.Alert(id="vault-modal-alert", is_open=False, color="danger", dismissable=True),
            # Campos: Select caixinha, Valor R$, etc.
            dbc.Row([
                dbc.Col(dbc.Label("Caixinha", className="fw-bold")),
                dbc.Col(dbc.Select(id="vault-select", options=[{"label": "Selecione...", "value": ""}]), width=12),
            ], className="my-3"),
            dbc.Row([
                dbc.Col(dbc.Label("Valor (R$)", className="fw-bold")),
                dbc.Col(dbc.InputGroup([dbc.InputGroupText("R$"), dbc.Input(id="vault-amount", type="number")]), width=12),
            ], className="my-3"),
        ]),
        dbc.ModalFooter([
            dbc.Button(["Cancelar"], id="vault-btn-cancel", color="secondary", outline=True, className="me-3"),
            dbc.Button(["Guardar"], id="vault-btn-allocate", color="success"),
            dbc.Button(["Resgatar"], id="vault-btn-withdraw", color="warning"),
        ]),
    ],
    id="vault-modal",
    is_open=False,
    size="md",
    backdrop="static",
)


def _render_vault_card(vault):
    """Renderiza Card único de caixinha com barra de progresso."""
    target = float(vault.target_amount or 0)
    saved = float(vault.saved_amount or 0)
    
    progress_pct = min((saved / target) * 100, 100) if target > 0 else 0
    
    return dbc.Card(
        className="h-100 border rounded mb-3 shadow-sm",
        children=[
            dbc.CardBody([
                html.Div([
                    html.Span("💰", className="me-2"),
                    html.H5(f"{vault.name}", className="mb-0 fw-bold"),
                    html.Small(
                        f"Meta: {target:,.2f} | Guardado: {saved:,.2f} ({progress_pct:.1f}%)",
                        className="text-muted mb-3",
                    ),
                    dbc.Progress([
                        dbc.ProgressBarBar(f"{progress_pct:.0f}%", id={"type": "vault-progress", "index": vault.id}),
                    ], value=progress_pct, color=["success" if progress_pct >= target else "primary"]),
                ]),
                # Botões de ação
                dbc.Row([
                    dbc.Col(dbc.Button("+ Guardar", id={"type": "vault-btn-keep", "index": vault.id}, color="success", size="sm")),
                    dbc.Col(dbc.Button("- Resgatar", id={"type": "vault-btn-take", "index": vault.id}, color="warning", size="sm"), className="ms-text-center"),
                ]),
            ])
        ],
    )


def layout():
    """Layout completo com alerta, cards e modais."""
    return dbc.Container([
        # Header (pode ser omitido para brevidade)
        html.H1(["Caixinhas", "text-muted"], className="mb-3"),
        
        dbc.Alert(id="vault-alert", is_open=False, color="danger", dismissable=True),

        # Cards container (rendizado dinâmico)
        html.Div(id="vaults-cards-container"),
        
        modal_vault,
    ], fluid=True, className="py-4 px-3")
