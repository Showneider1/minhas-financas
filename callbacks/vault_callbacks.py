"""Callbacks placeholders para Vault (Caixinhas) — UI mock temporário até deploy."

from dash import no_update, Input, Output, State, ctx
import dash_bootstrap_components as dbc

# Placeholder para evitar falha de importação durante testes e deploy.
# Implementação real com modais guardar/resgar será adicionada após push bem sucedido.

@app.callback(
    Output("vault-modal", "is_open"),
    Input("vault-btn-new", "n_clicks"),
    prevent_initial_call=True,
)
def toggle_vault_modal(n_clicks, **_):
    return True if n_clicks else no_update


@app.callback(
    Output("config-modals-feedback", "children", allow_duplicate=True),
    Input({"type": "vault-btn-act", "index": ALL}, "n_clicks"),
    State("auth-store", "data"),
    prevent_initial_call=True,
)
def handle_vault_action(n_clicks, auth_data):
    # Placeholder: validar n_clicks > 0 — P0 blindagem igual delete_conta.
    if not isinstance(getattr(n_clicks, "value", True), int) or (getattr(n_clicks, "value", None) <= 0):
        return no_update
    triggered = ctx.triggered_id
    # Fallback de validação — apenas placeholder para deploy.
    return dbc.Alert("Ação de Vault realizada.", color="success")

