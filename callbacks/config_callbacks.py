"""
Callbacks da página de configurações.
Arquitetura correta: botões de ação ficam no layout estático (configuracoes_page.py),
eliminando o bug de modal abrindo sozinho ao trocar de aba.
"""
from dash import Input, Output, State, no_update, ctx, html
import dash_bootstrap_components as dbc
from app import app
from database.connection import get_db_session
from services.account_service import AccountService
from services.category_service import CategoryService
from schemas.account_schema import AccountCreate, AccountType
from schemas.category_schema import CategoryCreate
from config.logging_config import app_logger


# ─── Helper de Toast ────────────────────────────────────────────────────────

def _toast(msg, color="success", icon="check-circle-fill"):
    return dbc.Toast(
        msg,
        header=[html.I(className=f"bi bi-{icon} me-2"), "Configurações"],
        is_open=True,
        dismissable=True,
        duration=4000,
        color=color,
        style={"position": "fixed", "bottom": "1.5rem", "right": "1.5rem",
               "zIndex": 9999, "minWidth": "280px"},
    )


# ─── 1. Botão de ação dinâmico no header (correto por aba) ───────────────────

@app.callback(
    Output("config-action-buttons", "children"),
    Input("tabs-configuracoes", "active_tab"),
)
def render_action_button(active_tab):
    """Renderiza o botão correto para cada aba no header — estático, sem recriar listas."""
    buttons = {
        "tab-categorias": dbc.Button(
            [html.I(className="bi bi-plus-lg me-2"), "Nova Categoria"],
            id="btn-open-cat-modal", color="primary", n_clicks=0,
        ),
        "tab-contas": dbc.Button(
            [html.I(className="bi bi-plus-lg me-2"), "Nova Conta"],
            id="btn-open-acc-modal", color="success", n_clicks=0,
        ),
        "tab-cartoes": dbc.Button(
            [html.I(className="bi bi-plus-lg me-2"), "Novo Cartão"],
            id="btn-open-card-modal", color="warning", n_clicks=0,
        ),
    }
    return buttons.get(active_tab, "")


# ─── 2. Renderização do conteúdo das abas (SEM botões) ───────────────────────

@app.callback(
    Output("content-configuracoes", "children"),
    Input("tabs-configuracoes",    "active_tab"),
    Input("trigger-update-config", "data"),
    State("store-user-id",         "data"),
)
def render_tab_content(active_tab, _, user_id):
    if not user_id:
        return dbc.Alert("Usuário não autenticado.", color="warning")
    with get_db_session() as db:
        if active_tab == "tab-categorias":
            return _render_categorias(db, user_id)
        elif active_tab == "tab-contas":
            return _render_contas(db, user_id, tipo="bank")
        elif active_tab == "tab-cartoes":
            return _render_contas(db, user_id, tipo="credit")
    return html.Div()


def _tipo_badge(transaction_type):
    if "INCOME" in str(transaction_type):
        return dbc.Badge("Receita", color="success", pill=True, className="ms-2")
    return dbc.Badge("Despesa", color="danger", pill=True, className="ms-2")


def _render_categorias(db, user_id):
    categorias = CategoryService(db).get_user_categories(user_id)

    if not categorias:
        return html.Div([
            html.I(className="bi bi-tags display-4 text-muted d-block text-center mb-3 mt-4"),
            html.P("Nenhuma categoria ainda. Clique em \"Nova Categoria\" para começar.",
                   className="text-center text-muted"),
        ], className="py-3")

    pais  = [c for c in categorias if not c.parent_id]
    items = []

    for pai in pais:
        is_system    = getattr(pai, "is_system", False)
        is_income    = "INCOME" in str(pai.transaction_type)
        folder_color = "text-success" if is_income else "text-danger"

        acoes = html.Small("Padrão", className="text-muted fst-italic") if is_system else (
            dbc.ButtonGroup([
                dbc.Button(html.I(className="bi bi-trash"),
                           id={"type": "btn-del-cat", "index": pai.id},
                           color="outline-danger", size="sm", n_clicks=0,
                           title="Excluir categoria"),
            ])
        )

        items.append(dbc.ListGroupItem([
            dbc.Row([
                dbc.Col([
                    html.I(className=f"bi bi-folder-fill {folder_color} me-2"),
                    html.Span(pai.name, className="fw-semibold"),
                    _tipo_badge(pai.transaction_type),
                ], className="d-flex align-items-center flex-wrap", width=True),
                dbc.Col(acoes, width="auto"),
            ], align="center"),
        ], className="border-0 rounded mb-1 bg-light py-2 px-3"))

        for filho in [c for c in categorias if c.parent_id == pai.id]:
            is_sys_filho = getattr(filho, "is_system", False)
            items.append(dbc.ListGroupItem([
                dbc.Row([
                    dbc.Col([
                        html.I(className="bi bi-arrow-return-right text-muted me-2 ms-4"),
                        html.Span(filho.name, className="small"),
                        _tipo_badge(filho.transaction_type),
                    ], className="d-flex align-items-center flex-wrap", width=True),
                    dbc.Col(
                        dbc.Button(html.I(className="bi bi-trash"),
                                   id={"type": "btn-del-cat", "index": filho.id},
                                   color="outline-danger", size="sm", n_clicks=0)
                        if not is_sys_filho else None,
                        width="auto",
                    ),
                ], align="center"),
            ], className="border-0 ps-3 mb-1 py-1"))

    return dbc.ListGroup(items, flush=True)


def _render_contas(db, user_id, tipo="bank"):
    all_acc = AccountService(db).get_user_accounts(user_id)

    if tipo == "credit":
        accs      = [a for a in all_acc if a.account_type == AccountType.CREDIT_CARD]
        empty_msg = "Nenhum cartão de crédito cadastrado."
    else:
        accs      = [a for a in all_acc if a.account_type != AccountType.CREDIT_CARD]
        empty_msg = "Nenhuma conta bancária cadastrada."

    if not accs:
        icon = "bi-credit-card" if tipo == "credit" else "bi-bank"
        return html.Div([
            html.I(className=f"bi {icon} display-4 text-muted d-block text-center mb-3 mt-4"),
            html.P(empty_msg, className="text-center text-muted"),
        ], className="py-3")

    cards = []
    for acc in accs:
        if tipo == "credit":
            details = [
                html.Hr(className="my-2"),
                dbc.Row([
                    dbc.Col([
                        html.Small("Limite", className="text-muted d-block"),
                        html.Strong(f"R$ {acc.credit_limit:,.2f}"),
                    ]),
                    dbc.Col([
                        dbc.Badge(f"Fecha {acc.closing_day}", color="info", className="me-1"),
                        dbc.Badge(f"Vence {acc.due_day}",    color="danger"),
                    ], className="text-end"),
                ]),
            ]
            icon = "bi-credit-card-fill text-warning"
        else:
            saldo_cls = "text-success" if acc.balance >= 0 else "text-danger"
            details = [
                html.Hr(className="my-2"),
                html.Small("Saldo Atual", className="text-muted d-block"),
                html.Strong(f"R$ {acc.balance:,.2f}", className=saldo_cls),
            ]
            icon = "bi-bank2 text-success"

        cards.append(dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.I(className=f"bi {icon} fs-3 me-3"),
                            html.Div([
                                html.H6(acc.name, className="mb-0 fw-bold"),
                                html.Small(acc.account_type.value, className="text-muted"),
                            ]),
                        ], className="d-flex align-items-center", width=True),
                        dbc.Col([
                            dbc.Button(html.I(className="bi bi-trash"),
                                       id={"type": "btn-del-acc", "index": acc.id},
                                       color="outline-danger", size="sm", n_clicks=0),
                        ], width="auto"),
                    ], align="center"),
                    *details,
                ])
            ], className="h-100 shadow-sm border-0"),
            width=12, md=6, lg=4, className="mb-4",
        ))

    return dbc.Row(cards)


# ─── 3. Modais — abrir/fechar ────────────────────────────────────────────────

@app.callback(
    Output("modal-categoria", "is_open"),
    Output("cat-parent",      "options"),
    Output("cat-nome",        "value"),
    Output("cat-tipo",        "value"),
    Output("cat-cor",         "value"),
    Output("cat-modal-feedback", "children"),
    Input("btn-open-cat-modal", "n_clicks"),
    Input("btn-cancel-cat",     "n_clicks"),
    Input("btn-save-cat",       "n_clicks"),
    State("store-user-id", "data"),
    prevent_initial_call=True,
)
def toggle_modal_categoria(n_open, n_cancel, n_save, user_id):
    triggered = ctx.triggered_id

    if triggered == "btn-open-cat-modal" and n_open and n_open > 0:
        options = []
        if user_id:
            with get_db_session() as db:
                cats    = CategoryService(db).get_user_categories(user_id)
                options = [{"label": c.name, "value": c.id}
                           for c in cats if not c.parent_id]
        return True, options, "", "EXPENSE", "#3498db", ""

    if triggered in ("btn-cancel-cat", "btn-save-cat"):
        return False, no_update, "", no_update, no_update, ""

    return no_update, no_update, no_update, no_update, no_update, no_update


@app.callback(
    Output("modal-conta", "is_open"),
    Output("acc-nome",    "value"),
    Output("acc-saldo",   "value"),
    Output("acc-modal-feedback", "children"),
    Input("btn-open-acc-modal", "n_clicks"),
    Input("btn-cancel-acc",     "n_clicks"),
    Input("btn-save-acc",       "n_clicks"),
    prevent_initial_call=True,
)
def toggle_modal_conta(n_open, n_cancel, n_save):
    triggered = ctx.triggered_id
    if triggered == "btn-open-acc-modal" and n_open and n_open > 0:
        return True, "", 0, ""
    if triggered in ("btn-cancel-acc", "btn-save-acc"):
        return False, no_update, no_update, ""
    return no_update, no_update, no_update, no_update


@app.callback(
    Output("modal-cartao",  "is_open"),
    Output("card-nome",     "value"),
    Output("card-modal-feedback", "children"),
    Input("btn-open-card-modal", "n_clicks"),
    Input("btn-cancel-card",     "n_clicks"),
    Input("btn-save-card",       "n_clicks"),
    prevent_initial_call=True,
)
def toggle_modal_cartao(n_open, n_cancel, n_save):
    triggered = ctx.triggered_id
    if triggered == "btn-open-card-modal" and n_open and n_open > 0:
        return True, "", ""
    if triggered in ("btn-cancel-card", "btn-save-card"):
        return False, no_update, ""
    return no_update, no_update, no_update


# ─── 4. Salvar dados ─────────────────────────────────────────────────────────

@app.callback(
    Output("trigger-update-config", "data"),
    Output("config-feedback",       "children"),
    Output("cat-modal-feedback",    "children", allow_duplicate=True),
    Output("acc-modal-feedback",    "children", allow_duplicate=True),
    Output("card-modal-feedback",   "children", allow_duplicate=True),
    Input("btn-save-cat",  "n_clicks"),
    Input("btn-save-acc",  "n_clicks"),
    Input("btn-save-card", "n_clicks"),
    State("cat-nome",  "value"), State("cat-tipo",  "value"),
    State("cat-cor",   "value"), State("cat-parent","value"),
    State("acc-nome",  "value"), State("acc-tipo",  "value"), State("acc-saldo","value"),
    State("card-nome", "value"), State("card-limite","value"),
    State("card-fechamento","value"), State("card-vencimento","value"),
    State("store-user-id",          "data"),
    State("trigger-update-config",  "data"),
    prevent_initial_call=True,
)
def save_data(
    n_cat, n_acc, n_card,
    cat_name, cat_type, cat_color, cat_parent,
    acc_name, acc_type, acc_balance,
    card_name, card_limit, card_close, card_due,
    user_id, trigger_val,
):
    triggered = ctx.triggered_id
    if not user_id:
        return no_update, no_update, no_update, no_update, no_update

    inline_err = dbc.Alert(
        "", color="danger", className="mb-0 py-2 mt-2 small", is_open=False
    )

    def _inline(msg):
        return dbc.Alert(msg, color="danger", className="mb-0 py-2 mt-2 small")

    try:
        with get_db_session() as db:
            if triggered == "btn-save-cat":
                if not cat_name or not cat_name.strip():
                    return no_update, no_update, _inline("Informe o nome da categoria."), no_update, no_update
                CategoryService(db).create_category(user_id, CategoryCreate(
                    name=cat_name.strip(),
                    transaction_type=cat_type,
                    color=cat_color,
                    parent_id=int(cat_parent) if cat_parent else None,
                ))
                return (trigger_val or 0)+1, _toast(f"Categoria \"{cat_name.strip()}\" criada!"), "", no_update, no_update

            elif triggered == "btn-save-acc":
                if not acc_name or not acc_name.strip():
                    return no_update, no_update, no_update, _inline("Informe o nome da conta."), no_update
                AccountService(db).create_account(user_id, AccountCreate(
                    name=acc_name.strip(),
                    account_type=AccountType(acc_type),
                    initial_balance=float(acc_balance or 0),
                    color="#2ecc71",
                ))
                return (trigger_val or 0)+1, _toast(f"Conta \"{acc_name.strip()}\" criada!", "success"), no_update, "", no_update

            elif triggered == "btn-save-card":
                if not card_name or not card_name.strip():
                    return no_update, no_update, no_update, no_update, _inline("Informe o nome do cartão.")
                AccountService(db).create_account(user_id, AccountCreate(
                    name=card_name.strip(),
                    account_type=AccountType.CREDIT_CARD,
                    initial_balance=0,
                    color="#e74c3c",
                    credit_limit=float(card_limit or 0),
                    closing_day=int(card_close or 1),
                    due_day=int(card_due or 10),
                ))
                return (trigger_val or 0)+1, _toast(f"Cartão \"{card_name.strip()}\" criado!", "warning"), no_update, no_update, ""

    except Exception as e:
        app_logger.error(f"Erro ao salvar configuração: {e}")
        return no_update, _toast(f"Erro: {e}", "danger", "exclamation-triangle-fill"), no_update, no_update, no_update

    return no_update, no_update, no_update, no_update, no_update


# ─── 5. Excluir categoria ────────────────────────────────────────────────────

@app.callback(
    Output("trigger-update-config", "data", allow_duplicate=True),
    Output("config-feedback",       "children", allow_duplicate=True),
    Input({"type": "btn-del-cat", "index": "__all__"}, "n_clicks"),
    State("store-user-id",         "data"),
    State("trigger-update-config", "data"),
    prevent_initial_call=True,
)
def delete_categoria(n_clicks, user_id, trigger_val):
    triggered = ctx.triggered_id
    if not isinstance(triggered, dict) or triggered.get("type") != "btn-del-cat":
        return no_update, no_update
    if user_id:
        cat_id = triggered["index"]
        try:
            with get_db_session() as db:
                CategoryService(db).delete_category(cat_id, user_id)
            return (trigger_val or 0)+1, _toast("Categoria excluída.", "secondary", "trash-fill")
        except Exception as e:
            return no_update, _toast(f"Erro ao excluir: {e}", "danger", "exclamation-triangle-fill")
    return no_update, no_update
