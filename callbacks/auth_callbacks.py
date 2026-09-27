"""
Callbacks de autenticação (login, registro, logout).
"""
from dash import Input, Output, State, no_update
import dash_bootstrap_components as dbc
from pydantic import ValidationError                          # ← ADICIONAR
from app import app
from database.connection import get_db_session
from services.auth_services import AuthService
from schemas.user_schema import UserCreate, UserLogin
from config.logging_config import app_logger
from middleware.rate_limiter import client_ip
from utils.exceptions import AppException


app_logger.info("Registrando callbacks de autenticação...")


@app.callback(
    [
        Output("auth-store", "data"),
        Output("auth-feedback", "children"),
        Output("url", "pathname"),
    ],
    Input("btn-login", "n_clicks"),
    State("login-email", "value"),
    State("login-password", "value"),
    prevent_initial_call=True,
)
def fazer_login(n_clicks, email, password):
    """Processa login do usuário."""
    try:
        if not n_clicks:
            return no_update, no_update, no_update

        if not email or not password:
            return no_update, dbc.Alert(
                "Preencha email e senha",
                color="warning",
                duration=3000,
                dismissable=True,
            ), no_update

        login_data = UserLogin(email=email, password=password)

        with get_db_session() as db:
            auth_service = AuthService(db)
            # P1: IP real alimenta o bucket anti-força-bruta.
            token_response = auth_service.authenticate_user(login_data, client_ip())

        auth_data = {
            "authenticated": True,
            "token": token_response.access_token,
            "refresh_token": token_response.refresh_token,
            "user_id": token_response.user_id,
            "email": token_response.email,
            "name": token_response.name or token_response.email,
        }

        app_logger.info("Login bem-sucedido (detalhes no audit log).")

        return auth_data, dbc.Alert(
            "Login realizado com sucesso!",
            color="success",
            duration=2000,
            dismissable=True,
        ), "/dashboard"

    except AppException as e:
        return no_update, dbc.Alert(
            str(e.message),
            color="danger",
            duration=4000,
            dismissable=True,
        ), no_update

    except ValidationError as e:                             # ← ADICIONAR
        erros = "; ".join([err["msg"] for err in e.errors()])
        return no_update, dbc.Alert(
            f"Dados inválidos: {erros}",
            color="danger",
            duration=5000,
            dismissable=True,
        ), no_update

    except Exception as e:
        app_logger.error(f"Erro inesperado no login: {e}")
        return no_update, dbc.Alert(
            "Não foi possível fazer login. Tente novamente.",
            color="danger",
            duration=4000,
            dismissable=True,
        ), no_update


@app.callback(
    [
        Output("auth-feedback-register", "children"),
        Output("url", "pathname", allow_duplicate=True),
    ],
    Input("btn-register", "n_clicks"),
    State("register-name", "value"),
    State("register-email", "value"),
    State("register-password", "value"),
    State("register-password-confirm", "value"),
    prevent_initial_call=True,
)
def fazer_registro(n_clicks, name, email, password, password_confirm):
    """Processa registro de novo usuário."""
    try:
        if not n_clicks:
            return no_update, no_update

        if not name or not email or not password or not password_confirm:
            return dbc.Alert("Preencha todos os campos", color="warning", duration=3000, dismissable=True), no_update

        if password != password_confirm:
            return dbc.Alert("As senhas não conferem", color="danger", duration=3000, dismissable=True), no_update

        if len(password) < 8:
            return dbc.Alert("A senha deve ter no mínimo 8 caracteres", color="warning", duration=3000, dismissable=True), no_update

        if not any(c.isdigit() for c in password):
            return dbc.Alert("A senha deve conter pelo menos um número", color="warning", duration=3000, dismissable=True), no_update

        if not any(c.isupper() for c in password):
            return dbc.Alert("A senha deve conter pelo menos uma letra maiúscula", color="warning", duration=3000, dismissable=True), no_update

        register_data = UserCreate(name=name, email=email, password=password)

        with get_db_session() as db:
            auth_service = AuthService(db)
            # P1: IP real alimenta o bucket anti-abuso de registro.
            auth_service.register_user(register_data, client_ip())

        app_logger.info("Novo usuário registrado (detalhes no audit log).")

        return dbc.Alert(
            "Conta criada com sucesso! Faça login para continuar.",
            color="success",
            duration=4000,
            dismissable=True,
        ), "/login"

    except AppException as e:
        return dbc.Alert(str(e.message), color="danger", duration=4000, dismissable=True), no_update

    except ValidationError as e:
        erros = "; ".join([err["msg"] for err in e.errors()])
        return dbc.Alert(f"Dados inválidos: {erros}", color="danger", duration=5000, dismissable=True), no_update

    except Exception as e:
        app_logger.error(f"Erro inesperado no registro: {e}")
        return dbc.Alert("Não foi possível criar a conta. Tente novamente.", color="danger", duration=4000, dismissable=True), no_update


@app.callback(
    [
        Output("auth-store", "clear_data"),
        Output("url", "pathname", allow_duplicate=True),
    ],
    Input("btn-logout", "n_clicks"),
    State("auth-store", "data"),
    prevent_initial_call=True,
)
def fazer_logout(n_clicks, auth_data):
    """Logout com revogação server-side da árvore de refresh (P1)."""
    if n_clicks and auth_data:
        try:
            user_id = auth_data.get("user_id")
            if user_id:
                with get_db_session() as db:
                    AuthService(db).logout(int(user_id))
        except Exception as e:
            app_logger.error(f"Erro no logout server-side: {e}")
        app_logger.info("Logout realizado (detalhes no audit log).")
        return True, "/login"

    return no_update, no_update


@app.callback(
    Output("store-user-id", "data"),
    Input("auth-store", "data"),
)
def atualizar_user_id(auth_data):
    """Espelho legado de user_id (NÃO é autoridade — ver auth_context).

    Mantido temporariamente para compatibilidade; callbacks P0 leem auth-store.
    """
    if auth_data and "user_id" in auth_data:
        return auth_data["user_id"]
    return None