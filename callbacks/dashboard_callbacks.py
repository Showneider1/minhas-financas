"""
Callbacks do Dashboard v7
- Saldo via get_saldo_calculado (dinâmico)
- Gráficos usam pagas + pendentes (get_category_breakdown_all)
- Fluxo mensal inclui pendentes do mês atual
"""
from dash import Input, Output, State, html, ctx, ALL, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime, date
from calendar import monthrange
import traceback

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


def _fim_do_mes(d: date) -> date:
    return d.replace(day=monthrange(d.year, d.month)[1])


# ─── KPIs ─────────────────────────────────────────────────────────────────────
@app.callback(
    Output("kpi-saldo",          "children"),
    Output("kpi-receita",        "children"),
    Output("kpi-despesa",        "children"),
    Output("kpi-resultado",      "children"),
    Output("kpi-resultado-info", "children"),
    Output("kpi-receita-info",   "children"),
    Output("kpi-despesa-info",   "children"),
    Input("dashboard-periodo",      "start_date"),
    Input("dashboard-periodo",      "end_date"),
    Input("store-reload-dashboard", "data"),
    Input("btn-update-dashboard",   "n_clicks"),
    State("store-user-id",          "data"),
)
def update_kpis(start_date, end_date, _reload, _btn, user_id):
    zero = "R$ 0,00"
    if not user_id:
        return zero, zero, zero, zero, "", f"Pendentes: {zero}", f"Pendentes: {zero}"

    ds, de = _parse_dates(start_date, end_date)
    fim_mes = _fim_do_mes(de)

    try:
        with get_db_session() as db:
            svc = DashboardService(db)
            data = svc.get_overview(user_id, ds, de)

            rec_paga  = data["receitas"]["pagas"]
            desp_paga = data["despesas"]["pagas"]

            # Inclui pendentes do período nas receitas/despesas exibidas
            rec_total  = data["receitas"]["total"]
            desp_total = data["despesas"]["total"]
            resultado  = rec_total - desp_total

            resultado_fmt  = _fmt_brl(resultado)
            resultado_info = "✅ Superávit" if resultado > 0 else ("⚠️ Déficit" if resultado < 0 else "—")

            rec_pend  = svc.get_pending_sum(user_id, TransactionType.INCOME,  ds, fim_mes)
            desp_pend = svc.get_pending_sum(user_id, TransactionType.EXPENSE, ds, fim_mes)

            # Saldo calculado dinamicamente (não depende de Account.balance)
            saldo = svc.get_saldo_calculado(user_id)

            return (
                _fmt_brl(saldo),
                _fmt_brl(rec_total),
                _fmt_brl(desp_total),
                resultado_fmt,
                resultado_info,
                f"Pagas: {_fmt_brl(rec_paga)} | Pend.: {_fmt_brl(rec_pend)}",
                f"Pagas: {_fmt_brl(desp_paga)} | Pend.: {_fmt_brl(desp_pend)}",
            )
    except Exception as e:
        app_logger.error(f"KPIs: {e}")
        traceback.print_exc()
        return "Erro", "Erro", "Erro", "Erro", "-", "-", "-"


# ─── Graficos + Tabela ────────────────────────────────────────────────────────
@app.callback(
    Output("grafico-fluxo-caixa",         "figure"),
    Output("grafico-categorias",          "figure"),
    Output("tabela-proximos-vencimentos", "children"),
    Output("tabela-top-categorias",       "children"),
    Output("totalizador-rec-pendente",    "children"),
    Output("totalizador-desp-pendente",   "children"),
    Output("totalizador-saldo-previsto",  "children"),
    Input("dashboard-periodo",            "start_date"),
    Input("dashboard-periodo",            "end_date"),
    Input("store-reload-dashboard",       "data"),
    Input("filtro-tipo-categoria",        "value"),
    State("store-user-id",                "data"),
)
def update_charts_and_table(start_date, end_date, _reload, tipo_cat, user_id):
    def empty_fig(msg="Nenhum dado no período"):
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

    try:
        tipo_enum = TransactionType(tipo_cat)
    except (ValueError, TypeError):
        tipo_enum = TransactionType.EXPENSE

    tipo_label = "despesas" if tipo_enum == TransactionType.EXPENSE else "receitas"
    blank      = html.Span("R$ 0,00", className="fw-bold small")

    if not user_id:
        return (empty_fig(), empty_fig(), html.P("Sem dados"),
                html.P("Sem dados"), "R$ 0,00", "R$ 0,00", blank)

    ds, de    = _parse_dates(start_date, end_date)
    fim_mes   = _fim_do_mes(de)
    days_ahead = max((fim_mes - date.today()).days, 0)

    fig1         = empty_fig()
    fig2         = empty_fig(f"Sem {tipo_label} no período")
    table        = html.Div()
    top_cats_div = html.Div()
    tot_rec      = "R$ 0,00"
    tot_desp     = "R$ 0,00"
    tot_saldo    = html.Span("R$ 0,00", className="fw-bold small")

    try:
        with get_db_session() as db:
            svc = DashboardService(db)

            # ── Fluxo mensal ──────────────────────────────────────────────────
            ev = svc.get_monthly_evolution(user_id, months=6)
            months_lbl = [i["month"] for i in ev["receitas"]]
            rec_vals   = [i["value"]  for i in ev["receitas"]]
            desp_vals  = [i["value"]  for i in ev["despesas"]]
            if any(v > 0 for v in rec_vals + desp_vals):
                fig1 = go.Figure()
                fig1.add_trace(go.Bar(x=months_lbl, y=rec_vals,  name="Receitas", marker_color="#2ecc71"))
                fig1.add_trace(go.Bar(x=months_lbl, y=desp_vals, name="Despesas", marker_color="#e74c3c"))
                fig1.update_layout(
                    barmode="group",
                    margin=dict(l=20, r=20, t=30, b=20),
                    legend=dict(orientation="h"),
                    template="plotly_white",
                )

            # ── Gráfico categorias — pagas + pendentes do período ─────────────
            cats = svc.get_category_breakdown_all(user_id, tipo_enum, ds, fim_mes)
            if cats:
                fig2 = go.Figure()
                fig2.add_trace(go.Pie(
                    labels=[f"{c['icon']} {c['name']}" for c in cats],
                    values=[c["total"] for c in cats],
                    hole=.5,
                    marker_colors=[c["color"] for c in cats],
                    textinfo="percent+label",
                    hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>",
                ))
                fig2.update_layout(
                    margin=dict(l=20, r=20, t=30, b=20),
                    showlegend=False,
                    template="plotly_white",
                )

            # ── Top Categorias ────────────────────────────────────────────────
            if cats:
                total_geral = sum(c["total"] for c in cats)
                bar_color   = "danger" if tipo_enum == TransactionType.EXPENSE else "success"
                val_color   = "#e74c3c" if tipo_enum == TransactionType.EXPENSE else "#2ecc71"
                rows_top = []
                for c in cats[:8]:
                    pct = (c["total"] / total_geral * 100) if total_geral > 0 else 0
                    rows_top.append(
                        html.Div([
                            html.Div([
                                html.Span(f"{c['icon']} {c['name']}", className="small fw-semibold"),
                                html.Span(_fmt_brl(c["total"]),
                                          className="small fw-bold float-end",
                                          style={"color": val_color}),
                            ]),
                            dbc.Progress(value=pct, style={"height": "4px"},
                                         color=bar_color, className="mb-2"),
                        ], className="mb-1")
                    )
                top_cats_div = html.Div(rows_top, className="px-1")
            else:
                top_cats_div = html.Div([
                    html.I(className="bi bi-inbox fs-2 text-muted"),
                    html.P(f"Sem {tipo_label} no período", className="text-muted small mt-2"),
                ], className="text-center py-4")

            # ── Próximos Vencimentos ──────────────────────────────────────────
            upcoming = svc.get_upcoming_transactions(user_id, days_ahead=days_ahead, limit=10)

            if not upcoming:
                table = html.Div([
                    html.I(className="bi bi-check-circle fs-1 text-success mb-2"),
                    html.P("Tudo em dia!", className="text-muted small"),
                ], className="text-center py-4")
            else:
                today_d = date.today()
                rows = []
                for t in upcoming:
                    if t.due_date is None:
                        continue
                    atrasado  = t.due_date < today_d
                    badge_cls = "badge bg-danger text-white" if atrasado else "badge bg-light text-dark border"
                    tipo_icon = (
                        "bi-arrow-down-circle-fill text-danger"
                        if t.transaction_type == TransactionType.EXPENSE
                        else "bi-arrow-up-circle-fill text-success"
                    )
                    val_cls = (
                        "text-danger fw-bold"
                        if t.transaction_type == TransactionType.EXPENSE
                        else "text-success fw-bold"
                    )
                    cat_icon = t.category.icon if t.category else "📝"
                    cat_name = t.category.name if t.category else "Geral"
                    amount   = getattr(t, "base_amount", None) or getattr(t, "amount", 0.0) or 0.0

                    btn_pay = html.Button(
                        html.I(className="bi bi-check-circle-fill text-success fs-5"),
                        id={"type": "btn-pay-upcoming", "index": t.id},
                        className="btn btn-link p-0 me-2",
                        title="Efetivar (abre edição)",
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
                            html.Span(t.description,
                                      className="fw-semibold text-truncate d-inline-block",
                                      style={"maxWidth": "140px"}),
                            html.Br(),
                            html.Small(f"{cat_icon} {cat_name}", className="text-muted"),
                        ]),
                        html.Td(_fmt_brl(amount), className=f"text-end {val_cls}"),
                        html.Td([btn_pay, btn_del], className="text-end",
                                style={"minWidth": "68px"}),
                    ], className="align-middle"))

                table = dbc.Table([html.Tbody(rows)],
                                  borderless=True, hover=True,
                                  responsive=True, className="align-middle mb-0")

            # ── Totalizadores ─────────────────────────────────────────────────
            sum_rec  = sum(
                getattr(t, "base_amount", None) or getattr(t, "amount", 0.0) or 0.0
                for t in upcoming
                if t.transaction_type == TransactionType.INCOME and t.due_date is not None
            )
            sum_desp = sum(
                getattr(t, "base_amount", None) or getattr(t, "amount", 0.0) or 0.0
                for t in upcoming
                if t.transaction_type == TransactionType.EXPENSE and t.due_date is not None
            )
            saldo_prev = sum_rec - sum_desp
            tot_rec    = _fmt_brl(sum_rec)
            tot_desp   = _fmt_brl(sum_desp)
            saldo_cls  = "text-success" if saldo_prev >= 0 else "text-danger"
            tot_saldo  = html.Span(_fmt_brl(saldo_prev), className=f"fw-bold small {saldo_cls}")

    except Exception as e:
        app_logger.error(f"Graficos/tabela: {e}")
        traceback.print_exc()

    return fig1, fig2, table, top_cats_div, tot_rec, tot_desp, tot_saldo


# ─── Sincronizar filtro Categoria ↔ Top Categorias ───────────────────────────
@app.callback(
    Output("filtro-tipo-top-categorias", "value"),
    Input("filtro-tipo-categoria",       "value"),
    prevent_initial_call=True,
)
def sincronizar_filtro_top(value):
    return value


# ─── Efetivar → abre modal de edição ─────────────────────────────────────────
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


# ─── Excluir → abre modal de confirmação ─────────────────────────────────────
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


# ─── Cancelar exclusão ────────────────────────────────────────────────────────
@app.callback(
    Output("modal-confirmar-exclusao", "is_open", allow_duplicate=True),
    Input("modal-excluir-btn-cancel",  "n_clicks"),
    prevent_initial_call=True,
)
def cancelar_exclusao(n):
    if not n:
        return no_update
    return False


# ─── Confirmar exclusão ───────────────────────────────────────────────────────
@app.callback(
    Output("modal-confirmar-exclusao", "is_open", allow_duplicate=True),
    Output("store-reload-aux",         "data"),
    Output("toast-dashboard",          "is_open"),
    Output("toast-dashboard",          "children"),
    Output("toast-dashboard",          "header"),
    Output("toast-dashboard",          "icon"),
    Input("modal-excluir-btn-ok",      "n_clicks"),
    State("store-acao-pendente",       "data"),
    State("store-user-id",             "data"),
    State("store-reload-aux",          "data"),
    prevent_initial_call=True,
)
def confirmar_exclusao(n_clicks, acao, user_id, reload_aux):
    if not n_clicks or not acao or not user_id:
        return no_update, no_update, no_update, no_update, no_update, no_update
    try:
        with get_db_session() as db:
            svc = DashboardService(db)
            svc.delete_transaction(acao["id"], user_id)
        return False, (reload_aux or 0) + 1, True, "Lançamento excluído.", "Excluído", "danger"
    except Exception as e:
        app_logger.error(f"Excluir: {e}")
        return False, no_update, True, str(e), "Erro", "warning"


# ─── Consolidador de reload ───────────────────────────────────────────────────
@app.callback(
    Output("store-reload-dashboard", "data", allow_duplicate=True),
    Input("store-reload-aux",        "data"),
    State("store-reload-dashboard",  "data"),
    prevent_initial_call=True,
)
def consolidar_reload(reload_aux, reload_counter):
    if reload_aux is None:
        return no_update
    return (reload_counter or 0) + 1