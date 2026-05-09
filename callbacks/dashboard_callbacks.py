"""
Callbacks do Dashboard v5
- KPI pendentes: busca ate fim do mes corrente (nao limita pelo end_date do filtro)
"""
from dash import Input, Output, State, html, ctx, ALL, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime, date
from calendar import monthrange

from app import app
from database.connection import get_db_session
from services.dashboard_service import DashboardService
from database.models.category import TransactionType
from config.logging_config import app_logger


def _fmt_brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def _parse_dates(start_date, end_date):
    try:
        ds = datetime.fromisoformat(start_date).date() if start_date else date.today().replace(day=1)
        de = datetime.fromisoformat(end_date).date()   if end_date   else date.today()
    except Exception:
        ds, de = date.today().replace(day=1), date.today()
    return ds, de


# ─── KPIs ─────────────────────────────────────────────────────────────────────
@app.callback(
    Output("kpi-saldo",        "children"),
    Output("kpi-receita",      "children"),
    Output("kpi-despesa",      "children"),
    Output("kpi-receita-info", "children"),
    Output("kpi-despesa-info", "children"),
    Input("dashboard-periodo",      "start_date"),
    Input("dashboard-periodo",      "end_date"),
    Input("store-reload-dashboard", "data"),
    Input("btn-update-dashboard",   "n_clicks"),
    State("store-user-id",          "data"),
)
def update_kpis(start_date, end_date, _reload, _btn, user_id):
    if not user_id:
        return "R$ 0,00", "R$ 0,00", "R$ 0,00", "Pendentes: R$ 0,00", "Pendentes: R$ 0,00"

    ds, de = _parse_dates(start_date, end_date)

    # Pendentes: sempre busca do inicio do mes do filtro ate o fim desse mesmo mes
    # para nao ficar zerado quando end_date = hoje mas ainda ha lancamentos futuros
    fim_mes = de.replace(day=monthrange(de.year, de.month)[1])

    try:
        with get_db_session() as db:
            svc = DashboardService(db)

            # Realizados (dentro do periodo filtrado, com paid_date)
            data = svc.get_overview(user_id, ds, de)

            # Pendentes: sem paid_date, due_date dentro do mes do filtro
            rec_pend  = svc._get_sum(user_id, TransactionType.INCOME,  ds, fim_mes, paid=False)
            desp_pend = svc._get_sum(user_id, TransactionType.EXPENSE, ds, fim_mes, paid=False)

            return (
                _fmt_brl(data["saldo"]["contas"]),
                _fmt_brl(data["receitas"]["pagas"]),
                _fmt_brl(data["despesas"]["pagas"]),
                f"Pendentes: {_fmt_brl(rec_pend)}",
                f"Pendentes: {_fmt_brl(desp_pend)}",
            )
    except Exception as e:
        app_logger.error(f"KPIs: {e}")
        return "Erro", "Erro", "Erro", "-", "-"


# ─── Graficos + Tabela ────────────────────────────────────────────────────────
@app.callback(
    Output("grafico-fluxo-caixa",         "figure"),
    Output("grafico-categorias",          "figure"),
    Output("tabela-proximos-vencimentos", "children"),
    Output("totalizador-rec-pendente",    "children"),
    Output("totalizador-desp-pendente",   "children"),
    Output("totalizador-saldo-previsto",  "children"),
    Input("dashboard-periodo",            "start_date"),
    Input("dashboard-periodo",            "end_date"),
    Input("store-reload-dashboard",       "data"),
    State("store-user-id",                "data"),
)
def update_charts_and_table(start_date, end_date, _reload, user_id):
    def empty_fig(msg="Nenhum dado no periodo"):
        f = go.Figure()
        f.update_layout(
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(visible=False), yaxis=dict(visible=False),
            annotations=[dict(text=msg, showarrow=False,
                              font=dict(size=13, color="#aaa"),
                              xref="paper", yref="paper", x=0.5, y=0.5)],
        )
        return f

    blank = ("R$ 0,00", "R$ 0,00", "R$ 0,00")
    if not user_id:
        return empty_fig(), empty_fig(), html.P("Sem dados"), *blank

    ds, de = _parse_dates(start_date, end_date)
    from calendar import monthrange
    fim_mes = de.replace(day=monthrange(de.year, de.month)[1])

    fig1 = empty_fig()
    fig2 = empty_fig("Sem despesas no periodo")
    table = html.Div()
    tot_rec = tot_desp = "R$ 0,00"
    tot_saldo = html.Span("R$ 0,00", className="fw-bold small text-success")

    try:
        with get_db_session() as db:
            svc = DashboardService(db)
            from dateutil.relativedelta import relativedelta

            # Fluxo mensal
            ev = svc.get_monthly_evolution(user_id, months=6)
            months_lbl = [i["month"] for i in ev["receitas"]]
            rec_vals   = [i["value"]  for i in ev["receitas"]]
            desp_vals  = [i["value"]  for i in ev["despesas"]]
            if any(v > 0 for v in rec_vals + desp_vals):
                fig1 = go.Figure()
                fig1.add_trace(go.Bar(x=months_lbl, y=rec_vals,  name="Receitas", marker_color="#2ecc71"))
                fig1.add_trace(go.Bar(x=months_lbl, y=desp_vals, name="Despesas", marker_color="#e74c3c"))
                fig1.update_layout(barmode="group", margin=dict(l=20, r=20, t=30, b=20),
                                   legend=dict(orientation="h"), template="plotly_white")

            # Categorias
            cats = svc.get_category_breakdown(user_id, TransactionType.EXPENSE, ds, de)
            if cats:
                fig2 = go.Figure()
                fig2.add_trace(go.Pie(
                    labels=[f"{c['icon']} {c['name']}" for c in cats],
                    values=[c["total"] for c in cats],
                    hole=.5,
                    marker_colors=[c["color"] for c in cats],
                ))
                fig2.update_layout(margin=dict(l=20, r=20, t=30, b=20),
                                   showlegend=False, template="plotly_white")

            # Proximos vencimentos (pendentes ate fim do mes)
            upcoming = svc.get_upcoming_transactions(user_id, days_ahead=30, limit=10)

            if not upcoming:
                table = html.Div([
                    html.I(className="bi bi-check-circle fs-1 text-success mb-2"),
                    html.P("Tudo em dia!", className="text-muted small"),
                ], className="text-center py-4")
            else:
                today = date.today()
                rows = []
                for t in upcoming:
                    atrasado  = t.due_date < today
                    badge_cls = "badge bg-danger text-white" if atrasado else "badge bg-light text-dark border"
                    tipo_icon = ("bi-arrow-down-circle-fill text-danger"
                                 if t.transaction_type == TransactionType.EXPENSE
                                 else "bi-arrow-up-circle-fill text-success")
                    val_cls  = ("text-danger fw-bold"
                                if t.transaction_type == TransactionType.EXPENSE
                                else "text-success fw-bold")
                    cat_icon = t.category.icon if t.category else "📝"
                    cat_name = t.category.name if t.category else "Geral"

                    btn_pay = html.Button(
                        html.I(className="bi bi-check-circle-fill text-success fs-5"),
                        id={"type": "btn-pay-upcoming", "index": t.id},
                        className="btn btn-link p-0 me-2",
                        title="Efetivar (abre edicao)",
                        n_clicks=0,
                    )
                    btn_del = html.Button(
                        html.I(className="bi bi-trash-fill text-danger fs-5"),
                        id={"type": "btn-del-upcoming", "index": t.id},
                        className="btn btn-link p-0",
                        title="Excluir",
                        n_clicks=0,
                    )

                    rows.append(html.Tr([
                        html.Td(html.Span(t.due_date.strftime("%d/%m"), className=badge_cls),
                                style={"width": "52px"}),
                        html.Td([
                            html.I(className=f"bi {tipo_icon} me-1"),
                            html.Span(t.description, className="fw-semibold text-truncate d-inline-block",
                                      style={"maxWidth": "140px"}),
                            html.Br(),
                            html.Small(f"{cat_icon} {cat_name}", className="text-muted"),
                        ]),
                        html.Td(_fmt_brl(t.base_amount), className=f"text-end {val_cls}"),
                        html.Td([btn_pay, btn_del], className="text-end", style={"minWidth": "68px"}),
                    ], className="align-middle"))

                table = dbc.Table(
                    [html.Tbody(rows)],
                    borderless=True, hover=True, responsive=True, className="align-middle mb-0"
                )

            # Totalizadores da tabela
            sum_rec  = sum(t.base_amount for t in upcoming if t.transaction_type == TransactionType.INCOME)
            sum_desp = sum(t.base_amount for t in upcoming if t.transaction_type == TransactionType.EXPENSE)
            saldo    = sum_rec - sum_desp
            tot_rec  = _fmt_brl(sum_rec)
            tot_desp = _fmt_brl(sum_desp)
            saldo_cls = "text-success" if saldo >= 0 else "text-danger"
            tot_saldo = html.Span(_fmt_brl(saldo), className=f"fw-bold small {saldo_cls}")

    except Exception as e:
        app_logger.error(f"Graficos/tabela: {e}")

    return fig1, fig2, table, tot_rec, tot_desp, tot_saldo


# ─── Efetivar → abre modal de edicao completo ────────────────────────────────
@app.callback(
    Output("modal-novo-lancamento",     "is_open", allow_duplicate=True),
    Output("store-transacao-id-editar", "data",    allow_duplicate=True),
    Input({"type": "btn-pay-upcoming",  "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def abrir_edicao_para_efetivar(pay_clicks):
    triggered = ctx.triggered_id
    if not triggered or not any(c for c in pay_clicks if c):
        return no_update, no_update
    return True, triggered["index"]


# ─── Excluir → abre modal de confirmacao ─────────────────────────────────────
@app.callback(
    Output("modal-confirmar-exclusao", "is_open"),
    Output("store-acao-pendente",      "data"),
    Input({"type": "btn-del-upcoming", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def abrir_modal_exclusao(del_clicks):
    triggered = ctx.triggered_id
    if not triggered or not any(c for c in del_clicks if c):
        return no_update, no_update
    return True, {"action": "delete", "id": triggered["index"]}


# ─── Cancelar exclusao ────────────────────────────────────────────────────────
@app.callback(
    Output("modal-confirmar-exclusao", "is_open", allow_duplicate=True),
    Input("modal-excluir-btn-cancel",  "n_clicks"),
    prevent_initial_call=True,
)
def cancelar_exclusao(n):
    if not n:
        return no_update
    return False


# ─── Confirmar exclusao ───────────────────────────────────────────────────────
@app.callback(
    Output("modal-confirmar-exclusao", "is_open", allow_duplicate=True),
    Output("store-reload-dashboard",   "data",    allow_duplicate=True),
    Output("toast-dashboard",          "is_open"),
    Output("toast-dashboard",          "children"),
    Output("toast-dashboard",          "header"),
    Output("toast-dashboard",          "icon"),
    Input("modal-excluir-btn-ok",      "n_clicks"),
    State("store-acao-pendente",       "data"),
    State("store-user-id",             "data"),
    State("store-reload-dashboard",    "data"),
    prevent_initial_call=True,
)
def confirmar_exclusao(n_clicks, acao, user_id, reload_counter):
    if not n_clicks or not acao or not user_id:
        return no_update, no_update, no_update, no_update, no_update, no_update
    try:
        with get_db_session() as db:
            svc = DashboardService(db)
            svc.delete_transaction(acao["id"], user_id)
        return False, (reload_counter or 0) + 1, True, "Lancamento excluido.", "Excluido", "danger"
    except Exception as e:
        app_logger.error(f"Excluir: {e}")
        return False, no_update, True, str(e), "Erro", "warning"
