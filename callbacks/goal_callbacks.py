"""
Callbacks da página de Metas Financeiras.
Arquivo: callbacks/goal_callbacks.py
"""
from dash import Input, Output, State, html, no_update, ctx
import dash_bootstrap_components as dbc
from datetime import datetime, timezone

from app import app
from database.connection import get_db_session
from services.goal_service import GoalService
from services.account_service import AccountService
from database.models.goal import GoalCategory, GoalStatus

# ─── Helpers ────────────────────────────────────────────────────────────────

CATEGORY_LABELS = {
    "emergency_fund": ("🛡️", "Reserva de Emergência"),
    "travel":         ("✈️",  "Viagem"),
    "education":      ("📚", "Educação"),
    "property":       ("🏠", "Imóvel"),
    "vehicle":        ("🚗", "Veículo"),
    "retirement":     ("🏖️", "Aposentadoria"),
    "investment":     ("📈", "Investimento"),
    "other":          ("🎯", "Outro"),
}

STATUS_BADGE = {
    "active":    ("success", "Ativa"),
    "completed": ("primary", "Concluída 🏆"),
    "paused":    ("warning", "Pausada"),
    "cancelled": ("danger",  "Cancelada"),
}


def _fmt_brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _progress_color(pct: float) -> str:
    if pct >= 100: return "success"
    if pct >= 60:  return "info"
    if pct >= 30:  return "warning"
    return "danger"


def _build_goal_card(g) -> dbc.Col:
    """Recebe um objeto Goal do SQLAlchemy e monta o card visual."""
    gid          = g.id
    status       = g.status.value
    cat          = g.category.value
    progress     = g.progress_percent
    remaining    = g.remaining_amount
    monthly      = g.suggested_monthly_contribution
    is_active    = status == "active"
    is_completed = status == "completed"

    cat_icon, cat_label = CATEGORY_LABELS.get(cat, ("🎯", "Outro"))
    badge_color, badge_label = STATUS_BADGE.get(status, ("secondary", status))

    deadline_str = ""
    if g.deadline:
        try:
            deadline_str = g.deadline.strftime("%d/%m/%Y")
        except Exception:
            pass

    monthly_info = (
        html.Small(f"Aporte sugerido: {_fmt_brl(monthly)}/mês", className="text-muted")
        if monthly and monthly > 0
        else html.Small("Sem prazo definido", className="text-muted")
    )

    return dbc.Col(
        dbc.Card([
            dbc.CardBody([
                # Cabeçalho
                dbc.Row([
                    dbc.Col([
                        html.Span(cat_icon, className="me-2 fs-4"),
                        html.Span(g.name, className="fw-bold fs-6"),
                    ], width=True),
                    dbc.Col([
                        dbc.Badge(badge_label, color=badge_color, className="ms-1"),
                    ], width="auto"),
                ], align="center", className="mb-2"),

                # Categoria e prazo
                html.Small([
                    html.I(className="bi bi-tag me-1 text-muted"),
                    cat_label,
                    html.Span([" · 📅 ", deadline_str], className="ms-2") if deadline_str else "",
                ], className="text-muted d-block mb-3"),

                # Progresso
                html.Div([
                    dbc.Row([
                        dbc.Col(html.Small(_fmt_brl(g.current_amount), className="text-success fw-bold")),
                        dbc.Col(html.Small(f"{progress:.1f}%", className="text-muted fw-bold text-end")),
                    ], className="mb-1"),
                    dbc.Progress(
                        value=min(progress, 100),
                        max=100,
                        color=_progress_color(progress),
                        style={"height": "10px", "borderRadius": "5px"},
                    ),
                    dbc.Row([
                        dbc.Col(monthly_info),
                        dbc.Col(
                            html.Small(["Meta: ", html.Strong(_fmt_brl(g.target_amount))],
                                       className="text-muted text-end"),
                            className="text-end",
                        ),
                    ], className="mt-1"),
                ], className="mb-3"),

                # Status especial para concluída
                dbc.Alert(
                    [html.I(className="bi bi-check-circle-fill me-2"), "Meta atingida! Parabéns! 🎉"],
                    color="success", className="py-2 mb-2 text-center fw-bold",
                ) if is_completed else html.Small(
                    [html.I(className="bi bi-bullseye me-1"), f"Faltam {_fmt_brl(remaining)}"],
                    className="text-muted d-block mb-3",
                ),

                # Botões
                dbc.ButtonGroup([
                    dbc.Button(
                        [html.I(className="bi bi-cash-coin me-1"), "Aportar"],
                        id={"type": "goal-btn-contribute", "index": gid},
                        color="success", outline=True, size="sm",
                        disabled=not is_active,
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-pencil me-1"), "Editar"],
                        id={"type": "goal-btn-edit", "index": gid},
                        color="primary", outline=True, size="sm",
                        disabled=is_completed,
                    ),
                    dbc.Button(
                        [html.I(className="bi bi-trash me-1"), "Excluir"],
                        id={"type": "goal-btn-delete", "index": gid},
                        color="danger", outline=True, size="sm",
                    ),
                ], size="sm", className="w-100"),
            ]),
        ], className="shadow-sm border-0 h-100"),
        width=12, md=6, lg=4, className="mb-4",
    )


# ─── 1. LISTAR METAS + KPIs ──────────────────────────────────────────────────

@app.callback(
    Output("goals-list-container", "children"),
    Output("goals-kpi-total",      "children"),
    Output("goals-kpi-current",    "children"),
    Output("goals-kpi-target",     "children"),
    Output("goals-kpi-progress",   "children"),
    Input("goals-reload-trigger",  "data"),
    Input("goals-filter-status",   "value"),
    Input("goals-filter-category", "value"),
    State("store-user-id", "data"),
    prevent_initial_call=False,
)
def load_goals(_, filter_status, filter_category, user_id):
    if not user_id:
        return (
            dbc.Alert("Faça login para ver suas metas.", color="warning"),
            "–", "–", "–", "–",
        )

    with get_db_session() as db:
        service         = GoalService(db)
        status_filter   = GoalStatus(filter_status)   if filter_status   else None
        category_filter = GoalCategory(filter_category) if filter_category else None
        goals           = service.list_goals(user_id, status=status_filter, category=category_filter)
        summary         = service.get_goals_summary(user_id)

    kpis = (
        str(summary.get("total_goals", 0)),
        _fmt_brl(summary.get("total_current", 0)),
        _fmt_brl(summary.get("total_target", 0)),
        f"{summary.get('overall_progress', 0):.1f}%",
    )

    if not goals:
        empty = html.Div([
            html.Div("🎯", className="display-1 text-center mb-3"),
            html.H5("Nenhuma meta encontrada", className="text-center text-muted"),
            html.P(
                'Crie sua primeira meta clicando em "Nova Meta".',
                className="text-center text-muted",
            ),
        ], className="py-5")
        return (empty, *kpis)

    cards = dbc.Row([_build_goal_card(g) for g in goals])
    return (cards, *kpis)


# ─── 2. ABRIR / FECHAR MODAL (NOVA / EDITAR) ─────────────────────────────────

@app.callback(
    Output("goal-modal",             "is_open"),
    Output("goal-modal-title",       "children"),
    Output("goal-edit-id",           "data"),
    Output("goal-input-name",        "value"),
    Output("goal-input-category",    "value"),
    Output("goal-input-target",      "value"),
    Output("goal-input-current",     "value"),
    Output("goal-input-deadline",    "date"),
    Output("goal-input-account",     "options"),
    Output("goal-input-account",     "value"),
    Output("goal-input-description", "value"),
    Output("goal-modal-feedback",    "children"),
    Input("goal-btn-new",          "n_clicks"),
    Input("goal-btn-cancel-modal", "n_clicks"),
    Input({"type": "goal-btn-edit", "index": "__all__"}, "n_clicks"),
    State("store-user-id", "data"),
    State("goal-modal",    "is_open"),
    prevent_initial_call=True,
)
def toggle_goal_modal(n_new, n_cancel, n_edits, user_id, is_open):
    triggered = ctx.triggered_id
    _blank = (False, no_update, None, "", "other", None, 0, None,
              [{"label": "Nenhuma", "value": ""}], "", "", "")

    if triggered == "goal-btn-cancel-modal":
        return _blank

    # Buscar contas do usuário
    account_options = [{"label": "Nenhuma", "value": ""}]
    if user_id:
        with get_db_session() as db:
            accounts = AccountService(db).get_accounts_by_user(user_id)
            account_options += [
                {"label": a.name, "value": str(a.id)}
                for a in accounts if a.is_active
            ]

    # Nova meta
    if triggered == "goal-btn-new":
        return (True, "Nova Meta Financeira", None, "", "other",
                None, 0, None, account_options, "", "", "")

    # Editar meta existente
    if isinstance(triggered, dict) and triggered.get("type") == "goal-btn-edit":
        goal_id = triggered["index"]
        if user_id:
            with get_db_session() as db:
                goal = GoalService(db).get_goal(goal_id, user_id)
                if goal:
                    dl = goal.deadline.date().isoformat() if goal.deadline else None
                    return (
                        True,
                        f"Editar Meta — {goal.name}",
                        goal.id,
                        goal.name,
                        goal.category.value,
                        goal.target_amount,
                        goal.current_amount,
                        dl,
                        account_options,
                        str(goal.account_id) if goal.account_id else "",
                        goal.description or "",
                        "",
                    )

    return (no_update,) * 12


# ─── 3. SALVAR META (CRIAR OU EDITAR) ────────────────────────────────────────

@app.callback(
    Output("goal-modal",           "is_open",  allow_duplicate=True),
    Output("goal-modal-feedback",  "children", allow_duplicate=True),
    Output("goals-reload-trigger", "data",     allow_duplicate=True),
    Input("goal-btn-save", "n_clicks"),
    State("goal-edit-id",           "data"),
    State("goal-input-name",        "value"),
    State("goal-input-category",    "value"),
    State("goal-input-target",      "value"),
    State("goal-input-current",     "value"),
    State("goal-input-deadline",    "date"),
    State("goal-input-account",     "value"),
    State("goal-input-description", "value"),
    State("store-user-id",          "data"),
    State("goals-reload-trigger",   "data"),
    prevent_initial_call=True,
)
def save_goal(n_clicks, edit_id, name, category, target, current,
              deadline, account_id, description, user_id, reload_counter):
    if not n_clicks:
        return no_update, no_update, no_update

    # Validações
    if not name or not name.strip():
        return no_update, dbc.Alert("⚠️ Informe o nome da meta.", color="danger", className="mb-0"), no_update
    if not target or float(target) <= 0:
        return no_update, dbc.Alert("⚠️ O valor alvo deve ser maior que zero.", color="danger", className="mb-0"), no_update

    try:
        target_val  = float(target)
        current_val = float(current or 0)
        deadline_dt = datetime.fromisoformat(deadline).replace(tzinfo=timezone.utc) if deadline else None
        acc_id      = int(account_id) if account_id else None
        cat_enum    = GoalCategory(category)
    except Exception as e:
        return no_update, dbc.Alert(f"Erro nos dados informados: {e}", color="danger", className="mb-0"), no_update

    try:
        with get_db_session() as db:
            service = GoalService(db)
            if edit_id:
                service.update_goal(
                    goal_id=edit_id, user_id=user_id,
                    name=name.strip(), category=cat_enum,
                    target_amount=target_val, current_amount=current_val,
                    deadline=deadline_dt, account_id=acc_id,
                    description=description,
                )
            else:
                service.create_goal(
                    user_id=user_id, name=name.strip(),
                    target_amount=target_val, category=cat_enum,
                    description=description, deadline=deadline_dt,
                    account_id=acc_id, current_amount=current_val,
                )
        return False, "", (reload_counter or 0) + 1

    except ValueError as e:
        return no_update, dbc.Alert(str(e), color="danger", className="mb-0"), no_update
    except Exception as e:
        return no_update, dbc.Alert(f"Erro inesperado: {e}", color="danger", className="mb-0"), no_update


# ─── 4. ABRIR MODAL DE APORTE ────────────────────────────────────────────────

@app.callback(
    Output("goal-contribution-modal",    "is_open"),
    Output("goal-contribution-id",       "data"),
    Output("goal-contribution-info",     "children"),
    Output("goal-contribution-amount",   "value"),
    Output("goal-contribution-feedback", "children"),
    Input({"type": "goal-btn-contribute", "index": "__all__"}, "n_clicks"),
    Input("goal-contribution-btn-cancel", "n_clicks"),
    State("store-user-id", "data"),
    prevent_initial_call=True,
)
def toggle_contribution_modal(n_contribute, n_cancel, user_id):
    triggered = ctx.triggered_id

    if triggered == "goal-contribution-btn-cancel":
        return False, None, "", None, ""

    if isinstance(triggered, dict) and triggered.get("type") == "goal-btn-contribute":
        goal_id = triggered["index"]
        if user_id:
            with get_db_session() as db:
                goal = GoalService(db).get_goal(goal_id, user_id)
                if goal:
                    info = dbc.Alert([
                        html.Strong(goal.name), html.Br(),
                        html.Small([
                            f"Acumulado: {_fmt_brl(goal.current_amount)}  |  ",
                            f"Meta: {_fmt_brl(goal.target_amount)}  |  ",
                            f"Progresso: {goal.progress_percent:.1f}%",
                        ]),
                    ], color="info", className="py-2 mb-0")
                    return True, goal_id, info, None, ""

    return no_update, no_update, no_update, no_update, ""


# ─── 5. CONFIRMAR APORTE ─────────────────────────────────────────────────────

@app.callback(
    Output("goal-contribution-modal",    "is_open",  allow_duplicate=True),
    Output("goal-contribution-feedback", "children", allow_duplicate=True),
    Output("goals-reload-trigger",       "data",     allow_duplicate=True),
    Input("goal-contribution-btn-save",  "n_clicks"),
    State("goal-contribution-id",     "data"),
    State("goal-contribution-amount", "value"),
    State("goal-contribution-type",   "value"),
    State("store-user-id",            "data"),
    State("goals-reload-trigger",     "data"),
    prevent_initial_call=True,
)
def save_contribution(n_clicks, goal_id, amount, contrib_type, user_id, reload_counter):
    if not n_clicks:
        return no_update, no_update, no_update

    if not amount or float(amount) <= 0:
        return (
            no_update,
            dbc.Alert("⚠️ Informe um valor maior que zero.", color="danger", className="mb-0"),
            no_update,
        )

    try:
        value = float(amount) * (-1 if contrib_type == "withdrawal" else 1)
        with get_db_session() as db:
            GoalService(db).add_contribution(goal_id, user_id, value)
        return False, "", (reload_counter or 0) + 1

    except ValueError as e:
        return no_update, dbc.Alert(str(e), color="danger", className="mb-0"), no_update
    except Exception as e:
        return no_update, dbc.Alert(f"Erro inesperado: {e}", color="danger", className="mb-0"), no_update


# ─── 6. EXCLUIR META ─────────────────────────────────────────────────────────

@app.callback(
    Output("goals-reload-trigger", "data", allow_duplicate=True),
    Input({"type": "goal-btn-delete", "index": "__all__"}, "n_clicks"),
    State("store-user-id",        "data"),
    State("goals-reload-trigger", "data"),
    prevent_initial_call=True,
)
def delete_goal(n_clicks, user_id, reload_counter):
    triggered = ctx.triggered_id
    if not isinstance(triggered, dict) or triggered.get("type") != "goal-btn-delete":
        return no_update
    if user_id:
        with get_db_session() as db:
            GoalService(db).delete_goal(triggered["index"], user_id)
    return (reload_counter or 0) + 1
