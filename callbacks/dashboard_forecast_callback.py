"""
Addon de callback: card de Projeção do Mês no Dashboard.
Adicione ao final do dashboard_callbacks.py existente (ou importe separado).
"""
from dash import Input, Output, State, html
import dash_bootstrap_components as dbc
from datetime import datetime, date

from app import app
from database.connection import get_db_session
from services.dashboard_service import DashboardService
from config.logging_config import app_logger

def _fmt(v: float) -> str:
    cor = "text-success" if v >= 0 else "text-danger"
    txt = f"R$ {abs(v):,.2f}".replace(",","X").replace(".",",").replace("X",".")
    sinal = "+" if v >= 0 else "-"
    return cor, f"{sinal} {txt}"

@app.callback(
    Output("dashboard-card-projecao", "children"),
    Input("dashboard-periodo",        "start_date"),
    Input("dashboard-periodo",        "end_date"),
    Input("store-reload-dashboard",   "data"),
    State("store-user-id",            "data"),
)
def update_forecast(start_date, end_date, _reload, user_id):
    if not user_id:
        return html.Div()

    try:
        dt_start = datetime.fromisoformat(start_date).date() if start_date else date.today().replace(day=1)
        dt_end   = datetime.fromisoformat(end_date).date()   if end_date   else date.today()
    except:
        dt_start = date.today().replace(day=1)
        dt_end   = date.today()

    try:
        with get_db_session() as db:
            data = DashboardService(db).get_forecast_balance(user_id, dt_start, dt_end)
    except Exception as e:
        app_logger.error(f"Projeção: {e}")
        return html.Div("Erro ao carregar projeção", className="text-danger")

    ef   = data["efetivado"]
    prev = data["previsto"]
    delta = data["delta"]

    ef_cls,   ef_txt   = _fmt(ef)
    prev_cls, prev_txt = _fmt(prev)
    delt_cls, delt_txt = _fmt(delta)

    prev_label = "🟢 Fecha no azul" if prev >= 0 else "🔴 Fecha no vermelho"

    card = dbc.Card([
        dbc.CardHeader(html.H6("📊 Projeção do Mês", className="mb-0 fw-bold")),
        dbc.CardBody([
            # Linha 1: Efetivado vs Previsto
            dbc.Row([
                dbc.Col([
                    html.Small("✅ Efetivado até hoje", className="text-muted d-block"),
                    html.Span(ef_txt, className=f"fs-5 fw-bold {ef_cls}"),
                ], width=6),
                dbc.Col([
                    html.Small("🔮 Previsto (mês todo)", className="text-muted d-block"),
                    html.Span(prev_txt, className=f"fs-5 fw-bold {prev_cls}"),
                ], width=6),
            ], className="mb-3"),

            # Barra de progresso visual efetivado/previsto
            _build_progress(ef, prev),

            html.Hr(className="my-2"),

            # Detalhes pendentes
            dbc.Row([
                dbc.Col([
                    html.Small("Receitas pendentes", className="text-muted"),
                    html.Div(
                        f"+ R$ {data['rec_pendente']:,.2f}".replace(",","X").replace(".",",").replace("X","."),
                        className="text-success small fw-semibold"),
                ], width=6),
                dbc.Col([
                    html.Small("Despesas pendentes", className="text-muted"),
                    html.Div(
                        f"- R$ {data['desp_pendente']:,.2f}".replace(",","X").replace(".",",").replace("X","."),
                        className="text-danger small fw-semibold"),
                ], width=6),
            ], className="mb-2"),

            # Badge de veredicto
            html.Div([
                dbc.Badge(prev_label, color="success" if prev >= 0 else "danger",
                          className="me-2 rounded-pill"),
                html.Small([
                    "Delta de ",
                    html.Span(delt_txt, className=f"fw-bold {delt_cls}"),
                    " ainda a realizar",
                ], className="text-muted"),
            ]),
        ]),
    ], className="shadow-sm border-0 mb-3")

    return card


def _build_progress(ef: float, prev: float):
    """Barra verde/cinza: quanto do previsto já foi efetivado."""
    if prev <= 0:
        pct = 100
    elif ef <= 0:
        pct = 0
    else:
        pct = min(100, round(ef / prev * 100))

    label = f"{pct}% efetivado"
    color = "success" if pct >= 70 else ("warning" if pct >= 40 else "danger")

    return html.Div([
        html.Small(label, className="text-muted mb-1 d-block"),
        dbc.Progress(value=pct, color=color, className="mb-1", style={"height": "8px"}),
    ])
