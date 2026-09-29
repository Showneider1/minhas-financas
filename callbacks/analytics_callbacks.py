"""Callbacks da página de Analytics."""

from decimal import Decimal

import plotly.graph_objects as go
from dash import Input, Output, State, no_update

from app import app
from config.logging_config import app_logger
from database.connection import get_db_session
from middleware.auth_context import resolve_user
from services.analytics_service import AnalyticsService
from utils.exceptions import AuthenticationError


def _fmt_brl(value) -> str:
    amount = value if isinstance(value, Decimal) else Decimal(str(value or 0))
    return f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _empty_figure(message: str) -> go.Figure:
    figure = go.Figure()
    figure.update_layout(
        margin=dict(l=20, r=20, t=30, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text=message,
                showarrow=False,
                font=dict(size=14, color="#95a5a6"),
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
            )
        ],
    )
    return figure


def _build_figures(auth_data, month, year):
    try:
        user_id = resolve_user(auth_data)
    except AuthenticationError:
        empty = _empty_figure("Sessão expirada — faça login novamente.")
        return empty, empty

    try:
        with get_db_session() as db:
            service = AnalyticsService(db)
            categories = service.get_expenses_by_category(user_id, month, year)
            cash_flow = service.get_cash_flow_history(user_id, limit_months=6)
    except Exception as exc:
        app_logger.error(f"Erro ao carregar analytics: {exc}")
        empty = _empty_figure("Não foi possível carregar os dados.")
        return empty, empty

    if not categories:
        expenses_figure = _empty_figure("Nenhuma despesa neste mês.")
    else:
        expenses_figure = go.Figure(
            data=[
                go.Pie(
                    labels=[f"{item['icon']} {item['name']}" for item in categories],
                    values=[float(item["total"]) for item in categories],
                    hole=0.55,
                    marker=dict(colors=[item["color"] for item in categories]),
                    textinfo="percent+label",
                    textfont=dict(size=12),
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "Total: R$ %{value:,.2f}<br>"
                        "Participação: %{percent}<extra></extra>"
                    ),
                )
            ]
        )
        expenses_figure.update_layout(
            margin=dict(l=20, r=20, t=30, b=20),
            showlegend=True,
            legend=dict(orientation="h", y=-0.15),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

    labels = [item["label"] for item in cash_flow]
    income_values = [float(item["income"]) for item in cash_flow]
    expense_values = [float(item["expenses"]) for item in cash_flow]

    cash_flow_figure = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=income_values,
                name="Receitas",
                marker_color="#2ecc71",
                hovertemplate=("<b>%{x}</b><br>Receitas: R$ %{y:,.2f}<extra></extra>"),
            ),
            go.Bar(
                x=labels,
                y=expense_values,
                name="Despesas",
                marker_color="#e74c3c",
                hovertemplate=("<b>%{x}</b>Despesas: R$ %{y:,.2f}<extra></extra>"),
            ),
        ]
    )
    cash_flow_figure.update_layout(
        barmode="group",
        margin=dict(l=20, r=20, t=30, b=30),
        legend=dict(orientation="h", y=-0.2),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(title="Valor (R$)", gridcolor="#f0f0f0"),
        xaxis=dict(title="Mês"),
    )

    return expenses_figure, cash_flow_figure


@app.callback(
    Output("analytics-expenses-category", "figure"),
    Output("analytics-cash-flow", "figure"),
    Input("url", "pathname"),
    State("auth-store", "data"),
    State("analytics-month", "value"),
    State("analytics-year", "value"),
    prevent_initial_call=False,
)
def load_analytics(pathname, auth_data, month, year):
    """Carrega os gráficos ao entrar na página de Analytics."""
    if pathname != "/analytics":
        return no_update, no_update
    return _build_figures(auth_data, month, year)


@app.callback(
    Output("analytics-expenses-category", "figure", allow_duplicate=True),
    Output("analytics-cash-flow", "figure", allow_duplicate=True),
    Input("analytics-month", "value"),
    Input("analytics-year", "value"),
    Input("store-reload-dashboard", "data"),
    State("auth-store", "data"),
    prevent_initial_call=True,
)
def update_analytics(month, year, _reload, auth_data):
    """Atualiza os gráficos quando o filtro muda ou dados são recarregados."""
    return _build_figures(auth_data, month, year)
