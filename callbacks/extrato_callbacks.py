"""
Callbacks do Extrato v4 — corrige salvar edição e comportamento de despesas pendentes.
"""

from calendar import monthrange
from datetime import date

import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, ctx, html, no_update

from app import app
from config.logging_config import app_logger
from database.connection import get_db_session
from database.enums import TransactionType
from database.repositories.transaction_repo import TransactionRepository
from middleware.auth_context import resolve_user
from services.account_service import AccountService
from services.category_service import CategoryService
from services.finance_service import FinanceService
from utils.exceptions import AuthenticationError

PAGE_SIZE = 30


def _fmt(v) -> str:
    # Borda de exibição: aceita Decimal/int/str (nunca faz aritmética aqui).
    from decimal import Decimal as _D

    amount = v if isinstance(v, _D) else _D(str(v))
    return f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _tx_to_dict(t) -> dict:
    """Serializa ORM → dict DENTRO da sessão para evitar DetachedInstanceError."""
    is_paid = t.paid_date is not None
    today = date.today()
    return {
        "id": t.id,
        "description": t.description or "",
        "notes": getattr(t, "notes", "") or "",
        "base_amount": t.base_amount,
        "type": t.transaction_type.value,
        "is_paid": is_paid,
        "is_overdue": not is_paid and t.due_date < today,
        "due_date": t.due_date,
        "paid_date": t.paid_date,
        "purchase_date": getattr(t, "purchase_date", None) or t.due_date,
        "cat_icon": (t.category.icon if t.category else "📝"),
        "cat_name": (t.category.name if t.category else "Sem categoria"),
        "cat_id": t.category_id,
        "account_name": (t.account.name if t.account else "-"),
        "account_id": t.account_id,
        "is_recurring": getattr(t, "is_recurring", False),
        "installment_number": getattr(t, "installment_number", 1) or 1,
        "total_installments": getattr(t, "total_installments", 1) or 1,
        "transaction_type": t.transaction_type.value,
    }


# ─── Carregar opções ──────────────────────────────────────────────────────────
@app.callback(
    Output("extrato-filter-account", "options"),
    Output("extrato-filter-category", "options"),
    Input("url", "pathname"),
    State("auth-store", "data"),
)
def load_filter_options(pathname, auth_data):
    if not auth_data or pathname != "/extrato":
        return no_update, no_update
    try:
        # P0 (IDOR): usuário derivado do JWT.
        user_id = resolve_user(auth_data)
        with get_db_session() as db:
            accs = AccountService(db).get_user_accounts(user_id)
            cats = CategoryService(db).get_user_categories(user_id)
            acc_opts = [{"label": "Todas as contas", "value": ""}] + [
                {"label": a.name, "value": a.id} for a in accs
            ]
            cat_opts = [{"label": "Todas", "value": ""}] + [
                {"label": f"{c.icon or ''} {c.name}", "value": c.id} for c in cats
            ]
        return acc_opts, cat_opts
    except AuthenticationError:
        return [], []
    except Exception as e:
        app_logger.error(f"Filtros extrato: {e}")
        return [], []


# ─── Limpar filtros ───────────────────────────────────────────────────────────
@app.callback(
    Output("extrato-filter-search", "value"),
    Output("extrato-filter-month", "value"),
    Output("extrato-filter-year", "value"),
    Output("extrato-filter-account", "value"),
    Output("extrato-filter-category", "value"),
    Output("extrato-filter-type", "value"),
    Output("extrato-filter-status", "value"),
    Output("extrato-page-current", "data"),
    Input("extrato-btn-clear", "n_clicks"),
    prevent_initial_call=True,
)
def clear_filters(n):
    if not n:
        return no_update
    return "", date.today().month, date.today().year, "", "", "ALL", "ALL", 1


# ─── Reset página ao mudar filtros ───────────────────────────────────────────
@app.callback(
    Output("extrato-page-current", "data", allow_duplicate=True),
    Input("extrato-filter-month", "value"),
    Input("extrato-filter-year", "value"),
    Input("extrato-filter-search", "value"),
    Input("extrato-filter-account", "value"),
    Input("extrato-filter-category", "value"),
    Input("extrato-filter-type", "value"),
    Input("extrato-filter-status", "value"),
    prevent_initial_call=True,
)
def reset_page(*_):
    return 1


# ─── Tabela principal ─────────────────────────────────────────────────────────
@app.callback(
    Output("extrato-table-container", "children"),
    Output("extrato-summary-cards", "children"),
    Output("extrato-result-count", "children"),
    Output("extrato-pagination", "children"),
    Input("extrato-filter-month", "value"),
    Input("extrato-filter-year", "value"),
    Input("extrato-filter-search", "value"),
    Input("extrato-filter-account", "value"),
    Input("extrato-filter-category", "value"),
    Input("extrato-filter-type", "value"),
    Input("extrato-filter-status", "value"),
    Input("extrato-reload-trigger", "data"),
    Input("extrato-page-current", "data"),
    State("auth-store", "data"),
)
def update_extrato(month, year, search, acc_id, cat_id, type_, status, _reload, page, auth_data):
    try:
        user_id = resolve_user(auth_data)
    except AuthenticationError:
        return html.Div("Sessão expirada — faça login novamente."), [], "", ""

    try:
        month = int(month or date.today().month)
        year = int(year or date.today().year)
        dt_start = date(year, month, 1)
        dt_end = date(year, month, monthrange(year, month)[1])

        acc_id = int(acc_id) if acc_id else None
        cat_id = int(cat_id) if cat_id else None
        type_f = None if type_ == "ALL" else TransactionType(type_)
        status_f = "PENDING" if status == "OVERDUE" else (None if status == "ALL" else status)

        with get_db_session() as db:
            repo = TransactionRepository(db)
            page = int(page or 1)
            txs, total = repo.filter_transactions(
                user_id=user_id,
                start_date=dt_start,
                end_date=dt_end,
                transaction_type=type_f,
                status=status_f,
                account_ids=[acc_id] if acc_id else None,
                category_ids=[cat_id] if cat_id else None,
                search=search,
                page=page,
                page_size=PAGE_SIZE,
            )
            summary = repo.get_filtered_summary(
                user_id=user_id,
                start_date=dt_start,
                end_date=dt_end,
                transaction_type=type_f,
                status=status_f,
                account_ids=[acc_id] if acc_id else None,
                category_ids=[cat_id] if cat_id else None,
                search=search,
            )
            rows_data = [_tx_to_dict(t) for t in txs]

        if status == "OVERDUE":
            rows_data = [t for t in rows_data if t["is_overdue"]]

        total_p = (summary["total"] + PAGE_SIZE - 1) // PAGE_SIZE
        cards = _build_summary_cards(
            summary["income"],
            summary["expense"],
            summary["income"] - summary["expense"],
            summary["pending_expense"],
        )
        count_label = f"{summary['total']} lançamento(s) encontrado(s)"

        if not rows_data:
            empty = html.Div(
                [
                    html.I(className="bi bi-search display-4 text-muted mb-3"),
                    html.H5("Nenhum lançamento encontrado", className="text-muted"),
                    html.P("Tente ajustar os filtros.", className="text-muted"),
                ],
                className="text-center py-5",
            )
            return empty, cards, count_label, ""

        rows = []
        for t in rows_data:
            is_income = t["type"] == "INCOME"
            is_transfer = t["type"] == "TRANSFER"
            val_cls = (
                "text-primary fw-bold"
                if is_transfer
                else ("text-success fw-bold" if is_income else "text-danger fw-bold")
            )
            signal = "" if is_transfer else ("+" if is_income else "-")

            if t["is_paid"]:
                badge = dbc.Badge("Pago", color="success", className="rounded-pill")
                data_show = t["paid_date"].strftime("%d/%m/%Y")
                label_data = "Data Pgto."
            elif t["is_overdue"]:
                badge = dbc.Badge("Atrasado", color="danger", className="rounded-pill")
                data_show = t["due_date"].strftime("%d/%m/%Y")
                label_data = "⚠ Vencido"
            else:
                badge = dbc.Badge(
                    "Pendente", color="warning", text_color="dark", className="rounded-pill"
                )
                data_show = t["due_date"].strftime("%d/%m/%Y")
                label_data = "Vencimento"

            notes_icon = (
                html.I(
                    className="bi bi-chat-left-text-fill text-info ms-1 small",
                    title=t["notes"],
                )
                if t["notes"]
                else ""
            )

            btn_edit = html.Button(
                html.I(className="bi bi-pencil-fill"),
                id={"type": "extrato-btn-edit", "index": t["id"]},
                className="btn btn-sm btn-light me-1",
                title="Editar",
                n_clicks=0,
            )
            btn_del = html.Button(
                html.I(className="bi bi-trash-fill text-danger"),
                id={"type": "extrato-btn-del", "index": t["id"]},
                className="btn btn-sm btn-light",
                title="Excluir",
                n_clicks=0,
            )

            rows.append(
                html.Tr(
                    [
                        html.Td(
                            [
                                html.Div(data_show, className="fw-bold"),
                                html.Small(label_data, className="text-muted"),
                            ]
                        ),
                        html.Td(
                            [
                                html.Div([t["description"], notes_icon], className="fw-semibold"),
                                html.Small(
                                    f"{t['cat_icon']} {t['cat_name']}", className="text-muted"
                                ),
                            ]
                        ),
                        html.Td(t["account_name"]),
                        html.Td(badge, className="text-center"),
                        html.Td(
                            f"{signal} {_fmt(t['base_amount'])}", className=f"text-end {val_cls}"
                        ),
                        html.Td(
                            html.Div([btn_edit, btn_del], className="d-flex justify-content-end"),
                            style={"whiteSpace": "nowrap"},
                        ),
                    ],
                    className="align-middle",
                )
            )

        table = dbc.Table(
            [
                html.Thead(
                    html.Tr(
                        [
                            html.Th("Data"),
                            html.Th("Descrição"),
                            html.Th("Conta"),
                            html.Th("Status", className="text-center"),
                            html.Th("Valor", className="text-end"),
                            html.Th("Ações", className="text-end"),
                        ]
                    )
                ),
                html.Tbody(rows),
            ],
            hover=True,
            responsive=True,
            striped=True,
            className="align-middle",
        )

        pagination = _build_pagination(page, total_p) if total_p > 1 else ""
        return table, cards, count_label, pagination

    except AuthenticationError:
        return html.Div("Sessão expirada — faça login novamente."), [], "", ""
    except Exception as e:
        app_logger.error(f"Extrato erro: {e}")
        return (
            html.Div("Erro ao carregar extrato. Tente novamente.", className="text-danger"),
            [],
            "",
            "",
        )


def _build_summary_cards(rec, desp, saldo, pend):
    saldo_cls = "text-success" if saldo >= 0 else "text-danger"
    return [
        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H6("Receitas (Filtro)", className="text-muted mb-1"),
                        html.H4(_fmt(rec), className="text-success fw-bold"),
                    ]
                ),
                className="shadow-sm border-0 border-start border-success border-4 h-100",
            ),
            md=3,
        ),
        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H6("Despesas (Filtro)", className="text-muted mb-1"),
                        html.H4(_fmt(desp), className="text-danger fw-bold"),
                    ]
                ),
                className="shadow-sm border-0 border-start border-danger border-4 h-100",
            ),
            md=3,
        ),
        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H6("Resultado", className="text-muted mb-1"),
                        html.H4(_fmt(saldo), className=f"{saldo_cls} fw-bold"),
                    ]
                ),
                className="shadow-sm border-0 border-start border-primary border-4 h-100",
            ),
            md=3,
        ),
        dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.H6("Despesas Pendentes", className="text-muted mb-1"),
                        html.H4(_fmt(pend), className="text-warning fw-bold"),
                        html.Small("Não pagas no período", className="text-muted"),
                    ]
                ),
                className="shadow-sm border-0 border-start border-warning border-4 h-100",
            ),
            md=3,
        ),
    ]


def _build_pagination(page, total):
    items = []
    items.append(
        dbc.PaginationItem(
            "«",
            disabled=(page == 1),
            id={"type": "extrato-page-btn", "index": max(1, page - 1)},
        )
    )
    for p in range(max(1, page - 2), min(total + 1, page + 3)):
        items.append(
            dbc.PaginationItem(
                str(p),
                active=(p == page),
                id={"type": "extrato-page-btn", "index": p},
            )
        )
    items.append(
        dbc.PaginationItem(
            "»",
            disabled=(page == total),
            id={"type": "extrato-page-btn", "index": min(total, page + 1)},
        )
    )
    return dbc.Pagination(items, className="mb-0")


# ─── Paginação ────────────────────────────────────────────────────────────────
@app.callback(
    Output("extrato-page-current", "data", allow_duplicate=True),
    Input({"type": "extrato-page-btn", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def go_to_page(clicks):
    triggered = ctx.triggered_id
    if not triggered or not any(c for c in clicks if c):
        return no_update
    return triggered["index"]


# ─── Editar: carrega dados no modal e abre ────────────────────────────────────
# CORREÇÃO: preenche o store-transacao-editar com os dados serializados
# para que o callback de salvar no modal_callbacks.py leia e popule os campos
@app.callback(
    Output("modal-novo-lancamento", "is_open", allow_duplicate=True),
    Output("store-transacao-id-editar", "data", allow_duplicate=True),
    Output("store-transacao-editar", "data", allow_duplicate=True),  # ← NOVO
    Input({"type": "extrato-btn-edit", "index": ALL}, "n_clicks"),
    State("auth-store", "data"),
    prevent_initial_call=True,
)
def editar_lancamento(clicks, auth_data):
    triggered = ctx.triggered_id
    if not triggered or not any(c for c in clicks if c):
        return no_update, no_update, no_update
    tx_id = triggered["index"]
    try:
        # P0 (IDOR): leitura com dono derivado do JWT.
        user_id = resolve_user(auth_data)
        with get_db_session() as db:
            repo = TransactionRepository(db)
            t = repo.get_with_relations(tx_id, user_id)
            if not t:
                return no_update, no_update, no_update
            dados = _tx_to_dict(t)  # serializa dentro da sessão
        return True, tx_id, dados
    except AuthenticationError:
        return no_update, no_update, no_update
    except Exception as e:
        app_logger.error(f"Editar extrato: {e}")
        return no_update, no_update, no_update


# ─── Excluir: abre modal de confirmação ──────────────────────────────────────
@app.callback(
    Output("extrato-modal-del", "is_open"),
    Output("extrato-del-id", "data"),
    Input({"type": "extrato-btn-del", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def abrir_del(clicks):
    triggered = ctx.triggered_id
    if not triggered or not any(c for c in clicks if c):
        return no_update, no_update
    return True, triggered["index"]


@app.callback(
    Output("extrato-modal-del", "is_open", allow_duplicate=True),
    Input("extrato-btn-cancel-del", "n_clicks"),
    prevent_initial_call=True,
)
def cancelar_del(n):
    return False if n else no_update


@app.callback(
    Output("extrato-modal-del", "is_open", allow_duplicate=True),
    Output("extrato-reload-trigger", "data", allow_duplicate=True),
    Output("extrato-toast", "is_open", allow_duplicate=True),
    Output("extrato-toast", "children", allow_duplicate=True),
    Output("extrato-toast", "header", allow_duplicate=True),
    Output("extrato-toast", "icon", allow_duplicate=True),
    Input("extrato-btn-confirm-del", "n_clicks"),
    State("extrato-del-id", "data"),
    State("auth-store", "data"),
    State("extrato-reload-trigger", "data"),
    prevent_initial_call=True,
)
def confirmar_del(n, del_id, auth_data, trigger):
    if not n or not del_id or not auth_data:
        return no_update, no_update, no_update, no_update, no_update, no_update
    try:
        # P0 (IDOR): exclusão com dono derivado do JWT.
        user_id = resolve_user(auth_data)
        with get_db_session() as db:
            FinanceService(db).delete_transaction(del_id, user_id)
        return False, (trigger or 0) + 1, True, "Lançamento excluído.", "Excluído", "danger"
    except AuthenticationError:
        return False, no_update, True, "Sessão expirada — faça login novamente.", "Erro", "warning"
    except Exception as e:
        app_logger.error(f"Del extrato: {e}")
        return False, no_update, True, "Não foi possível excluir.", "Erro", "warning"


# ─── Sincronizar com dashboard ────────────────────────────────────────────────
@app.callback(
    Output("extrato-reload-trigger", "data", allow_duplicate=True),
    Input("store-reload-dashboard", "data"),
    State("extrato-reload-trigger", "data"),
    prevent_initial_call=True,
)
def sync_reload(dashboard_reload, current):
    if not dashboard_reload:
        return no_update
    return (current or 0) + 1
