"""
Callbacks do Extrato v4 — corrige salvar edição e comportamento de despesas pendentes.
"""
from dash import Input, Output, State, html, ctx, ALL, no_update, dcc
import dash_bootstrap_components as dbc
from datetime import datetime, date

from app import app
from database.connection import get_db_session
from database.repositories.transaction_repo import TransactionRepository
from database.models.category import TransactionType
from schemas.transaction_schema import TransactionCreate
from services.account_service import AccountService
from services.category_service import CategoryService
from services.finance_service import FinanceService
from config.logging_config import app_logger

PAGE_SIZE = 30

def _fmt(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def _tx_to_dict(t) -> dict:
    """Serializa ORM → dict DENTRO da sessão para evitar DetachedInstanceError."""
    is_paid   = t.paid_date is not None
    today     = date.today()
    return {
        "id":              t.id,
        "description":     t.description or "",
        "notes":           getattr(t, "notes", "") or "",
        "base_amount":     t.base_amount,
        "type":            t.transaction_type.value,
        "is_paid":         is_paid,
        "is_overdue":      not is_paid and t.due_date < today,
        "due_date":        t.due_date,
        "paid_date":       t.paid_date,
        "purchase_date":   getattr(t, "purchase_date", None) or t.due_date,
        "cat_icon":        (t.category.icon  if t.category else "📝"),
        "cat_name":        (t.category.name  if t.category else "Sem categoria"),
        "cat_id":          t.category_id,
        "account_name":    (t.account.name   if t.account  else "-"),
        "account_id":      t.account_id,
        "is_recurring":    getattr(t, "is_recurring", False),
        "installment_number":  getattr(t, "installment_number", 1) or 1,
        "total_installments":  getattr(t, "total_installments", 1) or 1,
        "transaction_type": t.transaction_type.value,
    }

# ─── Carregar opções ──────────────────────────────────────────────────────────
@app.callback(
    Output("extrato-filter-account",  "options"),
    Output("extrato-filter-category", "options"),
    Input("url", "pathname"),
    State("store-user-id", "data"),
)
def load_filter_options(pathname, user_id):
    if not user_id or pathname != "/extrato":
        return no_update, no_update
    try:
        with get_db_session() as db:
            accs = AccountService(db).get_user_accounts(user_id)
            cats = CategoryService(db).get_user_categories(user_id)
            acc_opts = [{"label": "Todas as contas", "value": ""}] + [
                {"label": a.name, "value": a.id} for a in accs]
            cat_opts = [{"label": "Todas", "value": ""}] + [
                {"label": f"{c.icon or ''} {c.name}", "value": c.id} for c in cats]
        return acc_opts, cat_opts
    except Exception as e:
        app_logger.error(f"Filtros extrato: {e}")
        return [], []


# ─── Limpar filtros ───────────────────────────────────────────────────────────
@app.callback(
    Output("extrato-filter-search",   "value"),
    Output("extrato-filter-account",  "value"),
    Output("extrato-filter-category", "value"),
    Output("extrato-filter-type",     "value"),
    Output("extrato-filter-status",   "value"),
    Output("extrato-page-current",    "data"),
    Input("extrato-btn-clear",        "n_clicks"),
    prevent_initial_call=True,
)
def clear_filters(n):
    if not n:
        return no_update
    return "", "", "", "ALL", "ALL", 1


# ─── Reset página ao mudar filtros ───────────────────────────────────────────
@app.callback(
    Output("extrato-page-current", "data", allow_duplicate=True),
    Input("extrato-filter-date",     "start_date"),
    Input("extrato-filter-date",     "end_date"),
    Input("extrato-filter-search",   "value"),
    Input("extrato-filter-account",  "value"),
    Input("extrato-filter-category", "value"),
    Input("extrato-filter-type",     "value"),
    Input("extrato-filter-status",   "value"),
    prevent_initial_call=True,
)
def reset_page(*_):
    return 1


# ─── Tabela principal ─────────────────────────────────────────────────────────
@app.callback(
    Output("extrato-table-container", "children"),
    Output("extrato-summary-cards",   "children"),
    Output("extrato-result-count",    "children"),
    Output("extrato-pagination",      "children"),

    Input("extrato-filter-date",      "start_date"),
    Input("extrato-filter-date",      "end_date"),
    Input("extrato-filter-search",    "value"),
    Input("extrato-filter-account",   "value"),
    Input("extrato-filter-category",  "value"),
    Input("extrato-filter-type",      "value"),
    Input("extrato-filter-status",    "value"),
    Input("extrato-reload-trigger",   "data"),
    Input("extrato-page-current",     "data"),

    State("store-user-id", "data"),
)
def update_extrato(start_date, end_date, search, acc_id, cat_id,
                   type_, status, _reload, page, user_id):
    if not user_id:
        return html.Div("Usuário não identificado"), [], "", ""

    try:
        dt_start  = datetime.fromisoformat(start_date).date() if start_date else None
        dt_end    = datetime.fromisoformat(end_date).date()   if end_date   else None
        acc_id    = int(acc_id)  if acc_id  else None
        cat_id    = int(cat_id)  if cat_id  else None
        type_f    = type_  if type_  != "ALL" else None
        # OVERDUE é filtrado pós-query; no repo passa PENDING para já excluir os pagos
        status_f  = "PENDING" if status == "OVERDUE" else (status if status != "ALL" else None)

        with get_db_session() as db:
            repo    = TransactionRepository(db)
            raw_txs = repo.get_filtered(
                user_id=user_id,
                start_date=dt_start,
                end_date=dt_end,
                account_id=acc_id,
                category_id=cat_id,
                status=status_f,
                type_=type_f,
            )
            # ⚠️ Serializar DENTRO da sessão antes de fechar
            txs = [_tx_to_dict(t) for t in raw_txs]

        # Filtros pós-query
        if search:
            q   = search.lower()
            txs = [t for t in txs if q in t["description"].lower() or q in t["cat_name"].lower()]
        if status == "OVERDUE":
            txs = [t for t in txs if t["is_overdue"]]

        # Totais
        total_rec  = sum(t["base_amount"] for t in txs if t["type"] == "INCOME")
        total_desp = sum(t["base_amount"] for t in txs if t["type"] == "EXPENSE")
        total_pend = sum(t["base_amount"] for t in txs
                         if not t["is_paid"] and t["type"] == "EXPENSE")
        saldo = total_rec - total_desp

        cards       = _build_summary_cards(total_rec, total_desp, saldo, total_pend)
        count_label = f"{len(txs)} lançamento(s) encontrado(s)"

        if not txs:
            empty = html.Div([
                html.I(className="bi bi-search display-4 text-muted mb-3"),
                html.H5("Nenhum lançamento encontrado", className="text-muted"),
                html.P("Tente ajustar os filtros.", className="text-muted"),
            ], className="text-center py-5")
            return empty, cards, count_label, ""

        # Paginação
        page     = page or 1
        total_p  = (len(txs) + PAGE_SIZE - 1) // PAGE_SIZE
        page_txs = txs[(page - 1) * PAGE_SIZE : page * PAGE_SIZE]

        rows = []
        for t in page_txs:
            is_income = t["type"] == "INCOME"
            val_cls   = "text-success fw-bold" if is_income else "text-danger fw-bold"
            signal    = "+" if is_income else "-"

            if t["is_paid"]:
                badge      = dbc.Badge("Pago",     color="success",  className="rounded-pill")
                data_show  = t["paid_date"].strftime("%d/%m/%Y")
                label_data = "Data Pgto."
            elif t["is_overdue"]:
                badge      = dbc.Badge("Atrasado", color="danger",   className="rounded-pill")
                data_show  = t["due_date"].strftime("%d/%m/%Y")
                label_data = "⚠ Vencido"
            else:
                badge      = dbc.Badge("Pendente", color="warning",  text_color="dark", className="rounded-pill")
                data_show  = t["due_date"].strftime("%d/%m/%Y")
                label_data = "Vencimento"

            notes_icon = (
                html.I(className="bi bi-chat-left-text-fill text-info ms-1 small",
                       title=t["notes"])
                if t["notes"] else ""
            )

            btn_edit = html.Button(
                html.I(className="bi bi-pencil-fill"),
                id={"type": "extrato-btn-edit", "index": t["id"]},
                className="btn btn-sm btn-light me-1", title="Editar", n_clicks=0,
            )
            btn_del = html.Button(
                html.I(className="bi bi-trash-fill text-danger"),
                id={"type": "extrato-btn-del", "index": t["id"]},
                className="btn btn-sm btn-light", title="Excluir", n_clicks=0,
            )

            rows.append(html.Tr([
                html.Td([html.Div(data_show, className="fw-bold"),
                         html.Small(label_data, className="text-muted")]),
                html.Td([html.Div([t["description"], notes_icon], className="fw-semibold"),
                         html.Small(f"{t['cat_icon']} {t['cat_name']}", className="text-muted")]),
                html.Td(t["account_name"]),
                html.Td(badge, className="text-center"),
                html.Td(f"{signal} {_fmt(t['base_amount'])}",
                        className=f"text-end {val_cls}"),
                html.Td(html.Div([btn_edit, btn_del], className="d-flex justify-content-end"),
                        style={"whiteSpace": "nowrap"}),
            ], className="align-middle"))

        table = dbc.Table(
            [html.Thead(html.Tr([
                html.Th("Data"), html.Th("Descrição"), html.Th("Conta"),
                html.Th("Status", className="text-center"),
                html.Th("Valor",  className="text-end"),
                html.Th("Ações",  className="text-end"),
            ])),
             html.Tbody(rows)],
            hover=True, responsive=True, striped=True, className="align-middle",
        )

        pagination = _build_pagination(page, total_p) if total_p > 1 else ""
        return table, cards, count_label, pagination

    except Exception as e:
        app_logger.error(f"Extrato erro: {e}")
        import traceback; traceback.print_exc()
        return html.Div(f"Erro: {e}", className="text-danger"), [], "", ""


def _build_summary_cards(rec, desp, saldo, pend):
    saldo_cls = "text-success" if saldo >= 0 else "text-danger"
    return [
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Receitas (Filtro)", className="text-muted mb-1"),
            html.H4(_fmt(rec),   className="text-success fw-bold"),
        ]), className="shadow-sm border-0 border-start border-success border-4 h-100"), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Despesas (Filtro)", className="text-muted mb-1"),
            html.H4(_fmt(desp),  className="text-danger fw-bold"),
        ]), className="shadow-sm border-0 border-start border-danger border-4 h-100"), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Resultado", className="text-muted mb-1"),
            html.H4(_fmt(saldo), className=f"{saldo_cls} fw-bold"),
        ]), className="shadow-sm border-0 border-start border-primary border-4 h-100"), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H6("Despesas Pendentes", className="text-muted mb-1"),
            html.H4(_fmt(pend),  className="text-warning fw-bold"),
            html.Small("Não pagas no período", className="text-muted"),
        ]), className="shadow-sm border-0 border-start border-warning border-4 h-100"), md=3),
    ]


def _build_pagination(page, total):
    items = []
    items.append(dbc.PaginationItem(
        "«", disabled=(page == 1),
        id={"type": "extrato-page-btn", "index": max(1, page - 1)},
    ))
    for p in range(max(1, page - 2), min(total + 1, page + 3)):
        items.append(dbc.PaginationItem(
            str(p), active=(p == page),
            id={"type": "extrato-page-btn", "index": p},
        ))
    items.append(dbc.PaginationItem(
        "»", disabled=(page == total),
        id={"type": "extrato-page-btn", "index": min(total, page + 1)},
    ))
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
    Output("modal-novo-lancamento",     "is_open",   allow_duplicate=True),
    Output("store-transacao-id-editar", "data",      allow_duplicate=True),
    Output("store-transacao-editar",    "data",      allow_duplicate=True),   # ← NOVO
    Input({"type": "extrato-btn-edit",  "index": ALL}, "n_clicks"),
    State("store-user-id", "data"),
    prevent_initial_call=True,
)
def editar_lancamento(clicks, user_id):
    triggered = ctx.triggered_id
    if not triggered or not any(c for c in clicks if c):
        return no_update, no_update, no_update
    tx_id = triggered["index"]
    try:
        with get_db_session() as db:
            repo = TransactionRepository(db)
            t    = repo.get_with_relations(tx_id)
            if not t or t.user_id != user_id:
                return no_update, no_update, no_update
            dados = _tx_to_dict(t)   # serializa dentro da sessão
        return True, tx_id, dados
    except Exception as e:
        app_logger.error(f"Editar extrato: {e}")
        return no_update, no_update, no_update


# ─── Salvar edição ────────────────────────────────────────────────────────────
# CORREÇÃO PRINCIPAL: usa update_transaction com todos os campos corretos
@app.callback(
    Output("extrato-reload-trigger",    "data",   allow_duplicate=True),
    Output("store-reload-dashboard",    "data",   allow_duplicate=True),
    Output("extrato-toast",             "is_open"),
    Output("extrato-toast",             "children"),
    Output("extrato-toast",             "header"),
    Output("extrato-toast",             "icon"),
    Output("modal-novo-lancamento",     "is_open", allow_duplicate=True),
    Input("btn-salvar-lancamento",      "n_clicks"),
    State("store-transacao-id-editar",  "data"),
    State("input-descricao",            "value"),
    State("input-valor",                "value"),
    State("select-tipo",                "value"),
    State("select-categoria",           "value"),
    State("select-conta",               "value"),
    State("input-data-competencia",     "value"),
    State("input-data-vencimento",      "value"),
    State("input-data-pagamento",       "value"),
    State("input-parcela-atual",        "value"),
    State("input-total-parcelas",       "value"),
    State("check-recorrente",           "value"),
    State("input-notas",                "value"),
    State("store-user-id",              "data"),
    State("extrato-reload-trigger",     "data"),
    State("store-reload-dashboard",     "data"),
    prevent_initial_call=True,
)
def salvar_edicao(n_clicks, tx_id,
                  descricao, valor, tipo, categoria, conta,
                  dt_competencia, dt_vencimento, dt_pagamento,
                  parcela_atual, total_parcelas, recorrente, notas,
                  user_id, trigger_extrato, trigger_dash):

    if not n_clicks or not tx_id or not user_id:
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update

    # Validações básicas
    if not descricao or not valor or not tipo or not categoria or not conta:
        return (no_update, no_update, True,
                "Preencha todos os campos obrigatórios.", "Atenção", "warning", no_update)

    try:
        def parse_date(d):
            if not d:
                return None
            for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
                try:
                    return datetime.strptime(d, fmt).date()
                except ValueError:
                    pass
            return None

        purchase_date = parse_date(dt_competencia) or date.today()
        due_date      = parse_date(dt_vencimento)  or purchase_date
        paid_date     = parse_date(dt_pagamento)

        from database.models.category import TransactionType as TxType
        tx_type = TxType(tipo)

        tx_data = TransactionCreate(
            description=        descricao,
            base_amount=        float(str(valor).replace(",", ".")),
            transaction_type=   tx_type,
            category_id=        int(categoria),
            account_id=         int(conta),
            purchase_date=      purchase_date,
            due_date=           due_date,
            paid_date=          paid_date,
            is_recurring=       bool(recorrente),
            installment_number= int(parcela_atual  or 1),
            total_installments= int(total_parcelas or 1),
            notes=              notas,
        )

        with get_db_session() as db:
            service = FinanceService(db)
            service.update_transaction(tx_id, user_id, tx_data)

        return (
            (trigger_extrato or 0) + 1,
            (trigger_dash    or 0) + 1,
            True, "Lançamento atualizado com sucesso!", "Salvo", "success",
            False,  # fecha o modal
        )

    except Exception as e:
        app_logger.error(f"Salvar edição: {e}")
        import traceback; traceback.print_exc()
        return (no_update, no_update, True, f"Erro ao salvar: {e}", "Erro", "danger", no_update)


# ─── Excluir: abre modal de confirmação ──────────────────────────────────────
@app.callback(
    Output("extrato-modal-del", "is_open"),
    Output("extrato-del-id",    "data"),
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
    Output("extrato-modal-del",      "is_open",  allow_duplicate=True),
    Output("extrato-reload-trigger", "data",     allow_duplicate=True),
    Output("extrato-toast",          "is_open",  allow_duplicate=True),
    Output("extrato-toast",          "children", allow_duplicate=True),
    Output("extrato-toast",          "header",   allow_duplicate=True),
    Output("extrato-toast",          "icon",     allow_duplicate=True),
    Input("extrato-btn-confirm-del", "n_clicks"),
    State("extrato-del-id",          "data"),
    State("store-user-id",           "data"),
    State("extrato-reload-trigger",  "data"),
    prevent_initial_call=True,
)
def confirmar_del(n, del_id, user_id, trigger):
    if not n or not del_id or not user_id:
        return no_update, no_update, no_update, no_update, no_update, no_update
    try:
        with get_db_session() as db:
            FinanceService(db).delete_transaction(del_id, user_id)
        return False, (trigger or 0) + 1, True, "Lançamento excluído.", "Excluído", "danger"
    except Exception as e:
        app_logger.error(f"Del extrato: {e}")
        return False, no_update, True, str(e), "Erro", "warning"


# ─── Sincronizar com dashboard ────────────────────────────────────────────────
@app.callback(
    Output("extrato-reload-trigger", "data", allow_duplicate=True),
    Input("store-reload-dashboard",  "data"),
    State("extrato-reload-trigger",  "data"),
    prevent_initial_call=True,
)
def sync_reload(dashboard_reload, current):
    if not dashboard_reload:
        return no_update
    return (current or 0) + 1
