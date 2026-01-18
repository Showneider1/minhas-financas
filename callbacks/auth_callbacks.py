"""
Callbacks de autenticação (login, registro, logout).
"""
from dash import Input, Output, State, callback_context, no_update
import dash_bootstrap_components as dbc
from app import app
from database.connection import get_db_session
from services.auth_services import AuthService
from schemas.user_schema import UserCreate, UserLogin
from config.logging_config import app_logger
from utils.exceptions import AppException


print("🔐 Registrando callbacks de autenticação...")


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
    print(f"\n🔵 LOGIN CALLBACK EXECUTADO!")
    print(f"   - n_clicks: {n_clicks}")
    print(f"   - email: {email}")
    
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
            token_response = auth_service.authenticate_user(login_data)
        
        # ✅ CORRIGIDO: Adiciona campo "authenticated"
        auth_data = {
            "authenticated": True,  # ← ADICIONAR ESTA LINHA!
            "token": token_response.access_token,
            "user_id": token_response.user_id,
            "email": token_response.email,
        }
        
        print(f"   ✅ Login bem-sucedido! User ID: {token_response.user_id}")
        print(f"   ✅ Auth data: {auth_data}")
        
        return auth_data, dbc.Alert(
            "Login realizado com sucesso!",
            color="success",
            duration=2000,
            dismissable=True,
        ), "/dashboard"
    
    except AppException as e:
        print(f"   ❌ Erro: {e.message}")
        return no_update, dbc.Alert(
            str(e.message),
            color="danger",
            duration=4000,
            dismissable=True,
        ), no_update
    
    except Exception as e:
        print(f"   ❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        return no_update, dbc.Alert(
            f"Erro ao fazer login: {str(e)}",
            color="danger",
            duration=4000,
            dismissable=True,
        ), no_update


@app.callback(
    [
        Output("auth-feedback-register", "children"),
        Output("url", "pathname", allow_duplicate=True),  # allow_duplicate aqui
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
    print(f"\n🟢 REGISTRO CALLBACK EXECUTADO!")
    
    try:
        if not n_clicks:
            return no_update, no_update
        
        if not name or not email or not password or not password_confirm:
            return dbc.Alert(
                "Preencha todos os campos",
                color="warning",
                duration=3000,
                dismissable=True,
            ), no_update
        
        if password != password_confirm:
            return dbc.Alert(
                "As senhas não conferem",
                color="danger",
                duration=3000,
                dismissable=True,
            ), no_update
        
        if len(password) < 6:
            return dbc.Alert(
                "A senha deve ter no mínimo 6 caracteres",
                color="warning",
                duration=3000,
                dismissable=True,
            ), no_update
        
        register_data = UserCreate(
            name=name,
            email=email,
            password=password,
        )
        
        with get_db_session() as db:
            auth_service = AuthService(db)
            user = auth_service.register_user(register_data)
        
        print(f"   ✅ Usuário registrado! ID: {user.id}")
        
        return dbc.Alert(
            "Conta criada com sucesso! Faça login para continuar.",
            color="success",
            duration=4000,
            dismissable=True,
        ), "/login"
    
    except AppException as e:
        print(f"   ❌ Erro: {e.message}")
        return dbc.Alert(
            str(e.message),
            color="danger",
            duration=4000,
            dismissable=True,
        ), no_update
    
    except Exception as e:
        print(f"   ❌ Erro inesperado: {e}")
        return dbc.Alert(
            f"Erro ao criar conta: {str(e)}",
            color="danger",
            duration=4000,
            dismissable=True,
        ), no_update


@app.callback(
    [
        Output("auth-store", "clear_data"),
        Output("url", "pathname", allow_duplicate=True),  # allow_duplicate aqui
    ],
    Input("btn-logout", "n_clicks"),
    State("auth-store", "data"),
    prevent_initial_call=True,
)
def fazer_logout(n_clicks, auth_data):
    """Realiza logout do usuário."""
    print(f"\n🔴 LOGOUT CALLBACK EXECUTADO!")
    if n_clicks and auth_data:
        user_id = auth_data.get("user_id")
        print(f"   ✓ Logout: usuário {user_id}")
        return True, "/login"
    
    return no_update, no_update


@app.callback(
    Output("store-user-id", "data"),
    Input("auth-store", "data"),
)
def atualizar_user_id(auth_data):
    """Atualiza store de user_id quando auth muda."""
    if auth_data and "user_id" in auth_data:
        user_id = auth_data["user_id"]
        print(f"   ✓ Store user_id atualizado: {user_id}")
        return user_id
    return None


print("✅ Callbacks de autenticação registrados!")
