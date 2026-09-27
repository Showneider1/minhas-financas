"""
Addon de callback: card de Projeção do Mês no Dashboard.
Adicione ao final do dashboard_callbacks.py existente (ou importe separado).
"""

from datetime import date, datetime

import dash_bootstrap_components as dbc
from dash import Input, Output, State, html

from app import app
from config.logging_config import app_logger
from database.connection import get_db_session
from middleware.auth_context import resolve_user
from services.dashboard_service import DashboardService
from utils.exceptions import AuthenticationError


def _fmt(v) -> tuple:
    # Borda de exibição (sem aritmética aqui).
    from decimal import Decimal as _D

    amount = v if isinstance(v, _D) else _D(str(v or 0))
    cor = "text-success" if amount >= 0 else "text-danger"
    txt = f"R$ {abs(amount):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sinal = "+" if amount >= 0 else "-"
    return cor, f"{sinal} {txt}"


def _fmt_brl(v, *, positive: bool) -> str:
    # Borda de exibição com sinal explícito (sem aritmética aqui).
    from decimal import Decimal as _D

    amount = v if isinstance(v, _D) else _D(str(v or 0))
    txt = f"R$ {abs(amount):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"+ {txt}" if positive else f"- {txt}"


@app.callback(
    Output("dashboard-card-projecao", "children"),
    Input("dashboard-periodo", "start_date"),
    Input("dashboard-periodo", "end_date"),
    Input("store-reload-dashboard", "data"),
    State("auth-store", "data"),
)
def update_forecast(start_date, end_date, _reload, auth_data):
    try:
        # P0 (IDOR): usuário derivado do JWT.
        user_id = resolve_user(auth_data)
    except AuthenticationError:
        return html.Div()

    try:
        dt_start = (
            datetime.fromisoformat(start_date).date() if start_date else date.today().replace(day=1)
        )
        dt_end = datetime.fromisoformat(end_date).date() if end_date else date.today()
    except:
        dt_start = date.today().replace(day=1)
        dt_end = date.today()

    try:
        with get_db_session() as db:
            data = DashboardService(db).get_forecast_balance(user_id, dt_start, dt_end)
    except Exception as e:
        app_logger.error(f"Projeção: {e}")
        return html.Div("Erro ao carregar projeção", className="text-danger")

    ef = data["efetivado"]
    prev = data["previsto"]
    delta = data["delta"]

    ef_cls, ef_txt = _fmt(ef)
    prev_cls, prev_txt = _fmt(prev)
    delt_cls, delt_txt = _fmt(delta)

    prev_label = "🟢 Fecha no azul" if prev >= 0 else "🔴 Fecha no vermelho"

    card = dbc.Card(
        [
            dbc.CardHeader(html.H6("📊 Projeção do Mês", className="mb-0 fw-bold")),
            dbc.CardBody(
                [
                    # Linha 1: Efetivado vs Previsto
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Small(
                                        "✅ Efetivado até hoje", className="text-muted d-block"
                                    ),
                                    html.Span(ef_txt, className=f"fs-5 fw-bold {ef_cls}"),
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    html.Small(
                                        "🔮 Previsto (mês todo)", className="text-muted d-block"
                                    ),
                                    html.Span(prev_txt, className=f"fs-5 fw-bold {prev_cls}"),
                                ],
                                width=6,
                            ),
                        ],
                        className="mb-3",
                    ),
                    # Barra de progresso visual efetivado/previsto
                    _build_progress(ef, prev),
                    html.Hr(className="my-2"),
                    # Detalhes pendentes
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.Small("Receitas pendentes", className="text-muted"),
                                    html.Div(
                                        _fmt_brl(data["rec_pendente"], positive=True),
                                        className="text-success small fw-semibold",
                                    ),
                                ],
                                width=6,
                            ),
                            dbc.Col(
                                [
                                    html.Small("Despesas pendentes", className="text-muted"),
                                    html.Div(
                                        _fmt_brl(data["desp_pendente"], positive=False),
                                        className="text-danger small fw-semibold",
                                    ),
                                ],
                                width=6,
                            ),
                        ],
                        className="mb-2",
                    ),
                    # Badge de veredicto
                    html.Div(
                        [
                            dbc.Badge(
                                prev_label,
                                color="success" if prev >= 0 else "danger",
                                className="me-2 rounded-pill",
                            ),
                            html.Small(
                                [
                                    "Delta de ",
                                    html.Span(delt_txt, className=f"fw-bold {delt_cls}"),
                                    " ainda a realizar",
                                ],
                                className="text-muted",
                            ),
                        ]
                    ),
                ]
            ),
        ],
        className="shadow-sm border-0 mb-3",
    )

    return card


def _build_progress(ef, prev):
    """Barra verde/cinza: quanto do previsto já foi efetivado."""
    from decimal import Decimal as _D

    ef_d = ef if isinstance(ef, _D) else _D(str(ef or 0))
    prev_d = prev if isinstance(prev, _D) else _D(str(prev or 0))
    if prev_d <= 0:
        pct = 100
    elif ef_d <= 0:
        pct = 0
    else:
        pct = min(100, int(ef_d / prev_d * 100))

    label = f"{pct}% efetivado"
    color = "success" if pct >= 70 else ("warning" if pct >= 40 else "danger")

    return html.Div(
        [
            html.Small(label, className="text-muted mb-1 d-block"),
            dbc.Progress(value=pct, color=color, className="mb-1", style={"height": "8px"}),
        ]
    )
