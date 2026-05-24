"""
Página de login e registro.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc

# ===============================
# LAYOUT DE LOGIN
# ===============================

layout = dbc.Container(
    [
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardBody([
                            # Logo e Título
                            html.Div(
                                [
                                    html.I(className="bi bi-wallet2 fs-1 text-primary mb-3"),
                                    html.H2("Sistema Financeiro", className="fw-bold mb-1"),
                                    html.P("Faça login para continuar", className="text-muted"),
                                ],
                                className="text-center mb-4",
                            ),
                            
                            # Feedback
                            html.Div(id="auth-feedback"),
                            
                            # Formulário de Login
                            dbc.Form([
                                dbc.Label("Email", className="fw-bold"),
                                dbc.Input(
                                    id="login-email",
                                    type="email",
                                    placeholder="seu@email.com",
                                    className="mb-3",
                                ),
                                
                                dbc.Label("Senha", className="fw-bold"),
                                dbc.Input(
                                    id="login-password",
                                    type="password",
                                    placeholder="••••••••",
                                    className="mb-3",
                                ),
                                
                                dbc.Button(
                                    "Entrar",
                                    id="btn-login",
                                    color="primary",
                                    className="w-100 mb-3",
                                    size="lg",
                                ),
                                
                                html.Hr(),
                                
                                html.P(
                                    [
                                        "Não tem conta? ",
                                        dcc.Link("Criar conta", href="/register", className="fw-bold"),
                                    ],
                                    className="text-center mb-0",
                                ),
                            ]),
                        ]),
                    ],
                    className="shadow-lg border-0",
                ),
                width=12,
                lg=5,
            ),
            className="min-vh-100 align-items-center justify-content-center",
        ),
    ],
    fluid=True,
    className="bg-light",
)


# ===============================
# LAYOUT DE REGISTRO
# ===============================

register_layout = dbc.Container(
    [
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    [
                        dbc.CardBody([
                            # Logo e Título
                            html.Div(
                                [
                                    html.I(className="bi bi-wallet2 fs-1 text-primary mb-3"),
                                    html.H2("Criar Conta", className="fw-bold mb-1"),
                                    html.P("Preencha os dados abaixo", className="text-muted"),
                                ],
                                className="text-center mb-4",
                            ),
                            
                            # Feedback
                                                                                html.Div(id="auth-feedback-register"),
                            
                            # Formulário de Registro
                            dbc.Form([
                                dbc.Label("Nome Completo", className="fw-bold"),
                                dbc.Input(
                                    id="register-name",
                                    type="text",
                                    placeholder="Seu nome",
                                    className="mb-3",
                                ),
                                
                                dbc.Label("Email", className="fw-bold"),
                                dbc.Input(
                                    id="register-email",
                                    type="email",
                                    placeholder="seu@email.com",
                                    className="mb-3",
                                ),
                                
                                dbc.Label("Senha", className="fw-bold"),
                                dbc.Input(
                                    id="register-password",
                                    type="password",
                                    placeholder="••••••••",
                                    className="mb-3",
                                ),
                                
                                dbc.Label("Confirmar Senha", className="fw-bold"),
                                dbc.Input(
                                    id="register-password-confirm",
                                    type="password",
                                    placeholder="••••••••",
                                    className="mb-3",
                                ),
                                
                                dbc.Button(
                                    "Criar Conta",
                                    id="btn-register",
                                    color="success",
                                    className="w-100 mb-3",
                                    size="lg",
                                ),
                                
                                html.Hr(),
                                
                                html.P(
                                    [
                                        "Já tem conta? ",
                                        dcc.Link("Fazer login", href="/login", className="fw-bold"),
                                    ],
                                    className="text-center mb-0",
                                ),
                            ]),
                        ]),
                    ],
                    className="shadow-lg border-0",
                ),
                width=12,
                lg=5,
            ),
            className="min-vh-100 align-items-center justify-content-center",
        ),
    ],
    fluid=True,
    className="bg-light",
)
