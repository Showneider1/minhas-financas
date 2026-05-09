"""
Gráficos reutilizáveis com Plotly.
"""
import plotly.graph_objects as go
from typing import List, Dict


def line_chart(
    x_data: List,
    y_data: List,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    color: str = "#4F46E5",
):
    """
    Gráfico de linha simples.
    
    Args:
        x_data: Dados do eixo X
        y_data: Dados do eixo Y
        title: Título do gráfico
        x_label: Label do eixo X
        y_label: Label do eixo Y
        color: Cor da linha
    
    Returns:
        Plotly Figure
    """
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=x_data,
        y=y_data,
        mode='lines+markers',
        line=dict(color=color, width=3),
        marker=dict(size=8),
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family="Roboto, sans-serif"),
        hovermode='x unified',
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#F3F4F6')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#F3F4F6')
    
    return fig


def bar_chart(
    x_data: List,
    y_data: List,
    title: str = "",
    x_label: str = "",
    y_label: str = "",
    color: str = "#4F46E5",
    orientation: str = "v",
):
    """
    Gráfico de barras.
    
    Args:
        x_data: Dados do eixo X
        y_data: Dados do eixo Y
        title: Título
        x_label: Label X
        y_label: Label Y
        color: Cor das barras
        orientation: 'v' (vertical) ou 'h' (horizontal)
    
    Returns:
        Plotly Figure
    """
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=x_data if orientation == 'v' else y_data,
        y=y_data if orientation == 'v' else x_data,
        marker_color=color,
        orientation=orientation,
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family="Roboto, sans-serif"),
    )
    
    return fig


def pie_chart(
    labels: List[str],
    values: List[float],
    title: str = "",
    colors: List[str] = None,
    hole: float = 0.4,
):
    """
    Gráfico de pizza/donut.
    
    Args:
        labels: Labels das fatias
        values: Valores das fatias
        title: Título
        colors: Lista de cores personalizadas
        hole: Tamanho do buraco (0 = pizza, 0.4 = donut)
    
    Returns:
        Plotly Figure
    """
    if colors is None:
        colors = ['#EF4444', '#F97316', '#F59E0B', '#EAB308', '#84CC16', 
                 '#22C55E', '#10B981', '#14B8A6', '#06B6D4', '#0EA5E9']
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=hole,
        marker=dict(colors=colors),
        textinfo='label+percent',
        textposition='auto',
    )])
    
    fig.update_layout(
        title=title,
        showlegend=True,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family="Roboto, sans-serif"),
    )
    
    return fig


def multi_line_chart(
    data: List[Dict],
    title: str = "",
    x_label: str = "",
    y_label: str = "",
):
    """
    Gráfico de múltiplas linhas.
    
    Args:
        data: Lista de dicts com {name, x, y, color}
        title: Título
        x_label: Label X
        y_label: Label Y
    
    Returns:
        Plotly Figure
    """
    fig = go.Figure()
    
    for series in data:
        fig.add_trace(go.Scatter(
            x=series['x'],
            y=series['y'],
            mode='lines+markers',
            name=series['name'],
            line=dict(color=series.get('color', '#4F46E5'), width=3),
            marker=dict(size=8),
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title=x_label,
        yaxis_title=y_label,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family="Roboto, sans-serif"),
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#F3F4F6')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#F3F4F6')
    
    return fig


def gauge_chart(
    value: float,
    max_value: float,
    title: str = "",
    suffix: str = "",
):
    """
    Gráfico de gauge (velocímetro).
    
    Args:
        value: Valor atual
        max_value: Valor máximo
        title: Título
        suffix: Sufixo do valor (%, R$, etc)
    
    Returns:
        Plotly Figure
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': title},
        number={'suffix': suffix},
        gauge={
            'axis': {'range': [None, max_value]},
            'bar': {'color': "#4F46E5"},
            'steps': [
                {'range': [0, max_value * 0.5], 'color': "#E5E7EB"},
                {'range': [max_value * 0.5, max_value * 0.75], 'color': "#D1D5DB"},
                {'range': [max_value * 0.75, max_value], 'color': "#9CA3AF"},
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': max_value * 0.9
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor='white',
        font=dict(family="Roboto, sans-serif"),
        height=300,
    )
    
    return fig
