"""
Componentes de cards e inputs reutilizáveis.
"""
import dash_bootstrap_components as dbc
from dash import html
from typing import Optional, List


def kpi_card(
    title: str,
    value: str,
    icon: str = "bi-graph-up",
    color: str = "primary",
    subtitle: str = "",
):
    """
    Card de KPI (Key Performance Indicator).
    
    Args:
        title: Título do KPI
        value: Valor principal
        icon: Classe do ícone Bootstrap
        color: Cor do card (primary, success, danger, etc)
        subtitle: Subtítulo ou variação
    
    Returns:
        Component Dash
    """
    return dbc.Card(
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.I(className=f"{icon} fs-1 text-{color}"),
                ], width="auto"),
                dbc.Col([
                    html.P(title, className="text-muted mb-1 small"),
                    html.H3(value, className="mb-0 fw-bold", id=f"kpi-{title.lower().replace(' ', '-')}"),
                    html.Small(subtitle, className=f"text-{color}") if subtitle else html.Div(),
                ]),
            ], className="align-items-center"),
        ]),
        className="shadow-sm border-0 h-100",
    )


def radio_input(
    label: str,
    options: List[dict],
    input_id: str,
    value: Optional[str] = None,
    inline: bool = True,
):
    """
    Input de radio buttons.
    
    Args:
        label: Label do input
        options: Lista de dicts com {"label": str, "value": str}
        input_id: ID do componente
        value: Valor padrão selecionado
        inline: Se deve exibir inline
    
    Returns:
        Component Dash
    """
    return dbc.FormGroup([
        dbc.Label(label, className="fw-bold"),
        dbc.RadioItems(
            id=input_id,
            options=options,
            value=value,
            inline=inline,
        ),
    ])


def input_group(
    label: str,
    input_id: str,
    placeholder: str = "",
    input_type: str = "text",
    value: str = "",
    required: bool = False,
    help_text: str = "",
):
    """
    Input de texto com label.
    
    Args:
        label: Label do input
        input_id: ID do componente
        placeholder: Placeholder
        input_type: Tipo do input (text, email, password, number)
        value: Valor padrão
        required: Se é obrigatório
        help_text: Texto de ajuda
    
    Returns:
        Component Dash
    """
    return dbc.FormGroup([
        dbc.Label(label, className="fw-bold"),
        dbc.Input(
            id=input_id,
            type=input_type,
            placeholder=placeholder,
            value=value,
            required=required,
        ),
        dbc.FormText(help_text) if help_text else html.Div(),
    ], className="mb-3")


def input_text(
    input_id: str,
    placeholder: str = "",
    value: str = "",
    input_type: str = "text",
):
    """
    Input de texto simples (sem label).
    
    Args:
        input_id: ID do componente
        placeholder: Placeholder
        value: Valor padrão
        input_type: Tipo do input
    
    Returns:
        Component Dash
    """
    return dbc.Input(
        id=input_id,
        type=input_type,
        placeholder=placeholder,
        value=value,
    )


def select_input(
    label: str,
    select_id: str,
    options: List[dict],
    value: Optional[str] = None,
    placeholder: str = "Selecione...",
    required: bool = False,
):
    """
    Select dropdown com label.
    
    Args:
        label: Label do select
        select_id: ID do componente
        options: Lista de dicts com {"label": str, "value": str}
        value: Valor padrão selecionado
        placeholder: Placeholder
        required: Se é obrigatório
    
    Returns:
        Component Dash
    """
    return dbc.FormGroup([
        dbc.Label(label, className="fw-bold"),
        dbc.Select(
            id=select_id,
            options=options,
            value=value,
            placeholder=placeholder,
            required=required,
        ),
    ], className="mb-3")


def switch_input(
    label: str,
    switch_id: str,
    value: bool = False,
):
    """
    Switch toggle.
    
    Args:
        label: Label do switch
        switch_id: ID do componente
        value: Valor padrão
    
    Returns:
        Component Dash
    """
    return dbc.FormGroup([
        dbc.Checkbox(
            id=switch_id,
            label=label,
            value=value,
            className="form-switch",
        ),
    ], className="mb-3")


def textarea_input(
    label: str,
    textarea_id: str,
    placeholder: str = "",
    value: str = "",
    rows: int = 3,
):
    """
    Textarea com label.
    
    Args:
        label: Label do textarea
        textarea_id: ID do componente
        placeholder: Placeholder
        value: Valor padrão
        rows: Número de linhas
    
    Returns:
        Component Dash
    """
    return dbc.FormGroup([
        dbc.Label(label, className="fw-bold"),
        dbc.Textarea(
            id=textarea_id,
            placeholder=placeholder,
            value=value,
            rows=rows,
        ),
    ], className="mb-3")


def date_input(
    label: str,
    date_id: str,
    value: Optional[str] = None,
    min_date: Optional[str] = None,
    max_date: Optional[str] = None,
):
    """
    Input de data.
    
    Args:
        label: Label do input
        date_id: ID do componente
        value: Valor padrão (formato: YYYY-MM-DD)
        min_date: Data mínima
        max_date: Data máxima
    
    Returns:
        Component Dash
    """
    from dash import dcc
    
    return dbc.FormGroup([
        dbc.Label(label, className="fw-bold"),
        dcc.DatePickerSingle(
            id=date_id,
            date=value,
            min_date_allowed=min_date,
            max_date_allowed=max_date,
            display_format="DD/MM/YYYY",
            className="form-control",
        ),
    ], className="mb-3")
