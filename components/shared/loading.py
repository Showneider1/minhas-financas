"""
Componentes de loading e skeleton screens.
"""
import dash_bootstrap_components as dbc
from dash import html


def loading_spinner(
    text: str = "Carregando...",
    color: str = "primary",
    spinner_style: str = "border",
):
    """
    Spinner de loading simples.
    
    Args:
        text: Texto a exibir
        color: Cor do spinner (primary, secondary, etc)
        spinner_style: Estilo (border ou grow)
    
    Returns:
        Component Dash
    """
    return dbc.Spinner(
        html.Div(text, className="ms-3"),
        color=color,
        spinner_style=spinner_style,
    )


def skeleton_card():
    """
    Skeleton de um card para loading.
    
    Returns:
        Component Dash
    """
    return dbc.Card(
        dbc.CardBody([
            html.Div(
                className="placeholder-glow",
                children=[
                    html.Span(className="placeholder col-7 mb-2"),
                    html.Span(className="placeholder col-4"),
                    html.Span(className="placeholder col-4 mt-2"),
                    html.Span(className="placeholder col-6 mt-2"),
                    html.Span(className="placeholder col-8 mt-2"),
                ]
            )
        ]),
        className="mb-3",
    )


def skeleton_table(rows: int = 5):
    """
    Skeleton de uma tabela para loading.
    
    Args:
        rows: Número de linhas skeleton
    
    Returns:
        Component Dash
    """
    skeleton_rows = []
    
    for _ in range(rows):
        row = dbc.Card(
            dbc.CardBody(
                html.Div(
                    className="placeholder-glow",
                    children=[
                        dbc.Row([
                            dbc.Col(html.Span(className="placeholder col-10"), width=6),
                            dbc.Col(html.Span(className="placeholder col-6"), width=3),
                            dbc.Col(html.Span(className="placeholder col-8"), width=3),
                        ])
                    ]
                )
            ),
            className="mb-2 border-0",
        )
        skeleton_rows.append(row)
    
    return html.Div(skeleton_rows)


def skeleton_kpi():
    """
    Skeleton de um KPI card.
    
    Returns:
        Component Dash
    """
    return dbc.Card(
        dbc.CardBody([
            html.Div(
                className="placeholder-glow",
                children=[
                    html.Span(className="placeholder col-6 mb-2"),
                    html.Span(className="placeholder col-10", style={"height": "40px"}),
                    html.Span(className="placeholder col-8 mt-2"),
                ]
            )
        ]),
        className="shadow-sm border-0 h-100",
    )


def loading_overlay(show: bool = True):
    """
    Overlay de loading que cobre a tela inteira.
    
    Args:
        show: Se deve mostrar o overlay
    
    Returns:
        Component Dash
    """
    if not show:
        return html.Div()
    
    return html.Div(
        dbc.Spinner(
            html.Div(),
            color="primary",
            type="grow",
            spinner_style={"width": "3rem", "height": "3rem"},
        ),
        style={
            "position": "fixed",
            "top": 0,
            "left": 0,
            "width": "100%",
            "height": "100%",
            "backgroundColor": "rgba(0, 0, 0, 0.5)",
            "display": "flex",
            "justifyContent": "center",
            "alignItems": "center",
            "zIndex": 9999,
        }
    )


def empty_state(
    icon: str = "bi-inbox",
    title: str = "Nenhum dado disponível",
    description: str = "Não há informações para exibir no momento.",
    action_button: dict = None,
):
    """
    Estado vazio estilizado.
    
    Args:
        icon: Classe do ícone Bootstrap
        title: Título
        description: Descrição
        action_button: Dict com {text, id, color} para botão de ação
    
    Returns:
        Component Dash
    """
    children = [
        html.I(className=f"{icon} display-1 text-muted mb-3"),
        html.H4(title, className="text-muted mb-2"),
        html.P(description, className="text-muted small"),
    ]
    
    if action_button:
        button = dbc.Button(
            action_button.get("text", "Adicionar"),
            id=action_button.get("id"),
            color=action_button.get("color", "primary"),
            className="mt-3",
        )
        children.append(button)
    
    return dbc.Container(
        html.Div(
            children,
            className="text-center py-5",
        ),
        className="my-5",
    )
