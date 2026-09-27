"""
Callbacks da sidebar.
Fix: prevent_initial_call removido + url como trigger secundário
garante que nome/email apareçam corretamente ao navegar.
"""

from dash import Input, Output
from dash.exceptions import PreventUpdate

from app import app
from config.security import verify_token


@app.callback(
    Output("sidebar-user-name", "children"),
    Output("sidebar-user-email", "children"),
    Input("auth-store", "data"),
    Input("url", "pathname"),
    prevent_initial_call=False,
)
def atualizar_info_usuario(auth_data, _pathname):
    """Atualiza nome e e-mail do usuário na sidebar (só com sessão válida)."""
    if auth_data and isinstance(auth_data, dict):
        # P0: não exibe identidade com token expirado/adulterado.
        if verify_token(auth_data.get("token") or "") is None:
            raise PreventUpdate
        name = auth_data.get("name", "") or "Usuário"
        email = auth_data.get("email", "") or ""
        return name, email
    raise PreventUpdate
