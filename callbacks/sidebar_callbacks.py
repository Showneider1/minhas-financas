"""
Callbacks da sidebar.
Fix: prevent_initial_call removido + url como trigger secundário
garante que nome/email apareçam corretamente ao navegar.
"""
from dash import Input, Output
from dash.exceptions import PreventUpdate
from app import app


@app.callback(
    Output("sidebar-user-name",  "children"),
    Output("sidebar-user-email", "children"),
    Input("auth-store",  "data"),
    Input("url",         "pathname"),
    prevent_initial_call=False,
)
def atualizar_info_usuario(auth_data, _pathname):
    """Atualiza nome e e-mail do usuário na sidebar."""
    if auth_data and isinstance(auth_data, dict):
        name  = auth_data.get("name",  "") or "Usuário"
        email = auth_data.get("email", "") or ""
        return name, email
    raise PreventUpdate
