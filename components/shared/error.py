"""
Componentes de error handling e feedback.
"""
import dash_bootstrap_components as dbc
from dash import html


def error_alert(
    message: str,
    title: str = "Erro",
    dismissable: bool = True,
    color: str = "danger",
):
    """
    Alert de erro estilizado.
    
    Args:
        message: Mensagem de erro
        title: Título do erro
        dismissable: Se pode ser fechado
        color: Cor do alert
    
    Returns:
        Component Dash
    """
    return dbc.Alert(
        [
            html.H5(
                [html.I(className="bi bi-exclamation-triangle me-2"), title],
                className="alert-heading mb-2",
            ),
            html.P(message, className="mb-0"),
        ],
        color=color,
        dismissable=dismissable,
        className="shadow-sm",
    )


def success_toast(message: str, header: str = "Sucesso"):
    """
    Toast de sucesso.
    
    Args:
        message: Mensagem
        header: Cabeçalho
    
    Returns:
        Component Dash
    """
    return dbc.Toast(
        message,
        header=header,
        icon="success",
        duration=4000,
        is_open=True,
        style={"position": "fixed", "top": 20, "right": 20, "zIndex": 9999},
    )


def error_page_404():
    """
    Página de erro 404.
    
    Returns:
        Component Dash
    """
    return dbc.Container(
        html.Div(
            [
                html.I(className="bi bi-emoji-frown display-1 text-muted mb-4"),
                html.H1("404", className="display-1 fw-bold text-muted"),
                html.H4("Página não encontrada", className="mb-3"),
                html.P(
                    "A página que você está procurando não existe ou foi movida.",
                    className="text-muted mb-4",
                ),
                dbc.Button(
                    [html.I(className="bi bi-house me-2"), "Voltar ao Dashboard"],
                    href="/dashboard",
                    color="primary",
                    size="lg",
                ),
            ],
            className="text-center py-5",
        ),
        className="my-5",
    )


def error_boundary(error_message: str = None):
    """
    Error boundary para capturar erros de renderização.
    
    Args:
        error_message: Mensagem de erro
    
    Returns:
        Component Dash
    """
    return dbc.Container(
        dbc.Alert(
            [
                html.H4(
                    [html.I(className="bi bi-bug me-2"), "Ops! Algo deu errado"],
                    className="alert-heading",
                ),
                html.Hr(),
                html.P("Ocorreu um erro inesperado ao carregar esta página."),
                html.P(
                    error_message or "Por favor, tente recarregar a página ou entre em contato com o suporte.",
                    className="mb-0 small text-muted",
                ),
                html.Hr(),
                dbc.Button(
                    [html.I(className="bi bi-arrow-clockwise me-2"), "Recarregar"],
                    color="primary",
                    outline=True,
                    href="/",
                ),
            ],
            color="warning",
            className="mt-5",
        ),
    )


def validation_feedback(field_id: str, message: str, is_valid: bool = False):
    """
    Feedback de validação para campos de formulário.
    
    Args:
        field_id: ID do campo
        message: Mensagem
        is_valid: Se é válido ou inválido
    
    Returns:
        Component Dash
    """
    return html.Div(
        message,
        className=f"{'valid' if is_valid else 'invalid'}-feedback d-block",
        id=f"{field_id}-feedback",
    )
