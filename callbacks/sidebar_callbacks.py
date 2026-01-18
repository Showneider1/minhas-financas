"""
Callbacks da sidebar.
"""
from dash import Input, Output, State, callback_context, no_update
from dash.exceptions import PreventUpdate
from app import app


# REMOVIDO O CALLBACK DO MODAL - Agora está em transactions_callbacks


@app.callback(
    Output("sidebar-user-name", "children"),
    Output("sidebar-user-email", "children"),
    Input("auth-store", "data"),
    prevent_initial_call=True,
)
def atualizar_info_usuario(auth_data):
    """
    Atualiza informações do usuário na sidebar.
    """
    if auth_data and "email" in auth_data:
        name = auth_data.get("name", "Usuário")
        email = auth_data["email"]
        return name, email
    
    raise PreventUpdate
