"""
Callback do módulo de Projeção de Fluxo de Caixa (Predictive Analytics).

Gráfico de linha com o saldo projetado em conta corrente para os próximos
3 ou 6 meses. Áreas negativas são preenchidas em vermelho como alerta visual
de "Risco de Liquidez".
"""

from decimal import Decimal

import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash import Input, Output, State, html

from app import app
from config.logging_config import app_logger
from database.connection import get_db_session
from middleware.auth_context import resolve_user
from services.cash_flow_projection_service import CashFlowProjectionService
from utils.exceptions import AuthenticationError

ZERO = Decimal("0.00")


def _empty_figure(msg: str = "Sem dados para projetar") -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[
            dict(
                text=msg,
                showarrow=False,
                font=dict(size=13, color="#aaa"),
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
            )
        ],
    )
    return fig


def _build_figure(points: list[dict]) -> go.Figure:
    """Linha do saldo projetado + área vermelha nos trechos negativos."""
    dates = [p["date"] for p in points]
    # Borda Plotly/JSON: Decimal não serializa — float só aqui.
    balances = [float(p["projected_balance"]) for p in points]

    fig = go.Figure()

    # Linha de referência do zero (limite de liquidez).
    fig.add_hline(
        y=0,
        line_color="#e74c3c",
        line_width=1,
        line_dash="dash",
        annotation_text="Zero",
        annotation_position="bottom left",
        annotation_font=dict(size=10, color="#e74c3c"),
    )

    # Área vermelha APENAS onde a projeção é negativa (risco de liquidez).
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=[min(v, 0.0) for v in balances],
            mode="none",
            fill="tozeroy",
            fillcolor="rgba(231, 76, 60, 0.30)",
            line=dict(width=0),
            name="Risco de liquidez",
            hoverinfo="skip",
            showlegend=False,
        )
    )

    fig.add_trace(
        go.Scatter(
            x=dates,
            y=balances,
            mode="lines",
            name="Saldo projetado",
            line=dict(color="#0d6efd", width=2, shape="spline", smoothing=0.4),
            fill="tozeroy",
            fillcolor="rgba(13, 110, 253, 0.12)",
            hovertemplate="<b>%{x}</b><br>Saldo: R$ %{y:,.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        template="plotly_white",
        showlegend=False,
        hovermode="x unified",
        yaxis=dict(title="Saldo em conta (R$)", tickformat=",.2f", gridcolor="#eee"),
        xaxis=dict(title="Período", showgrid=False),
    )
    return fig


def _build_alert(points: list[dict]) -> object:
    """Faixa de risco de liquidez: primeiro dia negativo e pior saldo."""
    balances = [(p["date"], Decimal(p["projected_balance"])) for p in points]
    negativos = [(d, v) for d, v in balances if v < ZERO]

    if not negativos:
        return dbc.Alert(
            [
                html.I(className="bi bi-shield-check me-2"),
                "Sem risco de liquidez previsto no período: o saldo projetado nunca fica negativo.",
            ],
            color="success",
            className="mb-2 py-2",
        )

    primeiro_dia, primeiro_valor = negativos[0]
    pior_dia, pior_valor = min(negativos, key=lambda item: item[1])

    def brl(value: Decimal) -> str:
        txt = f"R$ {abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"- {txt}" if value < ZERO else txt

    return dbc.Alert(
        [
            html.I(className="bi bi-exclamation-triangle-fill me-2"),
            html.Span(
                [
                    "Risco de liquidez: saldo projetado fica negativo a partir de ",
                    html.Strong(f"{primeiro_dia}"),
                    f" ({brl(primeiro_valor)}).",
                ],
                className="d-block",
            ),
            html.Span(
                [
                    "Pior cenário: ",
                    html.Strong(pior_dia),
                    f" com {brl(pior_valor)}.",
                ],
                className="d-block small",
            ),
        ],
        color="danger",
        className="mb-2 py-2",
    )


@app.callback(
    Output("grafico-projecao-caixa", "figure"),
    Output("projecao-caixa-alerta", "children"),
    Input("projecao-caixa-horizonte", "value"),
    Input("store-reload-dashboard", "data"),
    Input("btn-update-dashboard", "n_clicks"),
    State("auth-store", "data"),
    prevent_initial_call=True,
)
def update_cash_flow_projection(horizonte, _reload, _btn, auth_data):
    try:
        user_id = resolve_user(auth_data)
    except AuthenticationError:
        return _empty_figure("Autenticação necessária"), html.Div()

    try:
        months_ahead = int(horizonte) if horizonte else 3
    except (TypeError, ValueError):
        months_ahead = 3
    if months_ahead < 1:
        months_ahead = 3

    try:
        with get_db_session() as db:
            points = CashFlowProjectionService(db).get_projected_daily_balance(
                user_id,
                months_ahead=months_ahead,
            )
    except Exception as e:  # noqa: BLE001
        app_logger.error(f"Projeção de fluxo de caixa: {e}")
        return _empty_figure("Erro ao carregar a projeção"), html.Div()

    if not points:
        return _empty_figure(), html.Div()

    return _build_figure(points), _build_alert(points)
