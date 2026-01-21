"""
Callbacks refatorados da página de configurações.
Lógica segura utilizando Services e Repositories.
"""
from dash import Input, Output, State, callback_context, no_update, html
import dash_bootstrap_components as dbc
from app import app
from database.connection import get_db_session
from services.account_service import AccountService
from services.category_service import CategoryService
from schemas.account_schema import AccountCreate, AccountType
from schemas.category_schema import CategoryCreate
from config.logging_config import app_logger

# =========================================================
# GESTÃO DE CONTEÚDO DAS ABAS
# =========================================================
@app.callback(
    Output("content-configuracoes", "children"),
    Input("tabs-configuracoes", "active_tab"),
    Input("trigger-update-config", "data"),
    State("store-user-id", "data"),
)
def render_tab_content(active_tab, _, user_id):
    if not user_id:
        return html.Div("Usuário não autenticado")

    with get_db_session() as db:
        if active_tab == "tab-categorias":
            return render_categorias_tab(db, user_id)
        elif active_tab == "tab-contas":
            return render_contas_tab(db, user_id, tipo="bank")
        elif active_tab == "tab-cartoes":
            return render_contas_tab(db, user_id, tipo="credit")
    
    return html.Div("Aba desconhecida")

# =========================================================
# FUNÇÕES DE RENDERIZAÇÃO (UI HELPERS)
# =========================================================
def render_categorias_tab(db, user_id):
    """Renderiza lista de categorias com visual moderno."""
    service = CategoryService(db)
    categorias = service.get_user_categories(user_id)
    
    # Botão de adicionar
    btn_add = dbc.Button(
        [html.I(className="bi bi-plus-lg me-2"), "Nova Categoria"],
        id="btn-open-cat-modal", color="primary", className="mb-4"
    )
    
    if not categorias:
        return html.Div([btn_add, html.P("Nenhuma categoria encontrada.")])
    
    # Organizar hierarquia visualmente
    items = []
    # Filtra pais
    pais = [c for c in categorias if not c.parent_id]
    
    for pai in pais:
        # Icone baseado no tipo
        color = "text-success" if str(pai.transaction_type) == "INCOME" else "text-danger"
        
        # Item Pai
        item_pai = dbc.ListGroupItem([
            html.Div([
                html.Span(html.I(className=f"bi bi-folder-fill {color} me-2"), className="fs-5"),
                html.Strong(pai.name),
                dbc.Badge("Sistema", color="light", text_color="dark", className="ms-2") if pai.is_system else None
            ], className="d-flex align-items-center")
        ], className="border-0 bg-light mb-1 rounded")
        items.append(item_pai)
        
        # Filhos
        filhos = [c for c in categorias if c.parent_id == pai.id]
        for filho in filhos:
            items.append(dbc.ListGroupItem([
                html.Div([
                    html.I(className="bi bi-arrow-return-right text-muted me-2 ms-3"),
                    html.Span(filho.name),
                ], className="d-flex align-items-center small")
            ], className="border-0 ps-4"))

    return html.Div([btn_add, dbc.ListGroup(items, flush=True)])

def render_contas_tab(db, user_id, tipo="bank"):
    """Renderiza Contas ou Cartões."""
    service = AccountService(db)
    all_accounts = service.get_user_accounts(user_id)
    
    # Filtragem Python (idealmente seria no DB, mas o service get_all pega tudo)
    if tipo == "credit":
        accounts = [a for a in all_accounts if a.account_type == AccountType.CREDIT_CARD]
        btn_id = "btn-open-card-modal"
        btn_label = "Novo Cartão"
        btn_color = "warning"
        empty_msg = "Nenhum cartão de crédito cadastrado."
    else:
        accounts = [a for a in all_accounts if a.account_type != AccountType.CREDIT_CARD]
        btn_id = "btn-open-acc-modal"
        btn_label = "Nova Conta"
        btn_color = "success"
        empty_msg = "Nenhuma conta bancária cadastrada."

    # Grid de Cards
    cards = []
    for acc in accounts:
        if tipo == "credit":
            # Card Visual de Cartão de Crédito
            details = [
                html.Hr(className="my-2"),
                html.Div([
                    html.Small("Limite", className="text-muted d-block"),
                    html.Strong(f"R$ {acc.credit_limit:,.2f}")
                ], className="mb-2"),
                html.Div([
                    html.Badge(f"Fecha dia {acc.closing_day}", color="info", className="me-1"),
                    html.Badge(f"Vence dia {acc.due_day}", color="danger"),
                ])
            ]
            icon = "bi-credit-card-fill"
        else:
            # Card Visual de Conta Bancária
            details = [
                html.Hr(className="my-2"),
                html.Div([
                    html.Small("Saldo Atual", className="text-muted d-block"),
                    html.Strong(f"R$ {acc.balance:,.2f}", className="text-success" if acc.balance >= 0 else "text-danger")
                ])
            ]
            icon = "bi-bank2"

        card = dbc.Col(dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.I(className=f"bi {icon} fs-2 text-primary"),
                    html.Div([
                        html.H5(acc.name, className="card-title mb-0"),
                        html.Small(acc.account_type.value, className="text-muted")
                    ], className="ms-3")
                ], className="d-flex align-items-center mb-2"),
                *details
            ])
        ], className="h-100 shadow-sm border-0"), width=12, md=6, lg=4, className="mb-4")
        cards.append(card)

    btn_add = dbc.Button(
        [html.I(className="bi bi-plus-lg me-2"), btn_label],
        id=btn_id, color=btn_color, className="mb-4"
    )

    if not cards:
        return html.Div([btn_add, html.P(empty_msg, className="text-muted")])

    return html.Div([btn_add, dbc.Row(cards)])

# =========================================================
# CALLBACKS DE MODAL E SALVAMENTO
# =========================================================

# --- ABRIR/FECHAR MODAIS ---
@app.callback(
    [Output("modal-categoria", "is_open"), Output("cat-parent", "options")],
    [Input("btn-open-cat-modal", "n_clicks"), Input("btn-save-cat", "n_clicks")],
    [State("modal-categoria", "is_open"), State("store-user-id", "data")],
    prevent_initial_call=True
)
def toggle_cat_modal(n1, n2, is_open, user_id):
    ctx = callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    
    options = []
    if trigger == "btn-open-cat-modal" and user_id:
        # Popula select de pais
        with get_db_session() as db:
            cats = CategoryService(db).get_user_categories(user_id)
            # Apenas categorias que não são subcategorias podem ser pais
            options = [{"label": c.name, "value": c.id} for c in cats if c.parent_id is None]
        return True, options
        
    return False, no_update

@app.callback(
    Output("modal-conta", "is_open"),
    [Input("btn-open-acc-modal", "n_clicks"), Input("btn-save-acc", "n_clicks")],
    State("modal-conta", "is_open"),
    prevent_initial_call=True
)
def toggle_acc_modal(n1, n2, is_open):
    if n1 or n2: return not is_open
    return is_open

@app.callback(
    Output("modal-cartao", "is_open"),
    [Input("btn-open-card-modal", "n_clicks"), Input("btn-save-card", "n_clicks")],
    State("modal-cartao", "is_open"),
    prevent_initial_call=True
)
def toggle_card_modal(n1, n2, is_open):
    if n1 or n2: return not is_open
    return is_open

# --- SALVAR DADOS ---

@app.callback(
    Output("trigger-update-config", "data"),
    Output("config-feedback", "children"),
    
    # Triggers
    Input("btn-save-cat", "n_clicks"),
    Input("btn-save-acc", "n_clicks"),
    Input("btn-save-card", "n_clicks"),
    
    # States Categoria
    State("cat-nome", "value"), State("cat-tipo", "value"), State("cat-cor", "value"), State("cat-parent", "value"),
    
    # States Conta
    State("acc-nome", "value"), State("acc-tipo", "value"), State("acc-saldo", "value"),
    
    # States Cartão
    State("card-nome", "value"), State("card-limite", "value"), State("card-fechamento", "value"), State("card-vencimento", "value"),
    
    # User
    State("store-user-id", "data"),
    prevent_initial_call=True
)
def save_data(
    btn_cat, btn_acc, btn_card, 
    cat_name, cat_type, cat_color, cat_parent,
    acc_name, acc_type, acc_balance,
    card_name, card_limit, card_close, card_due,
    user_id
):
    ctx = callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if not user_id: return no_update, no_update

    try:
        with get_db_session() as db:
            if trigger == "btn-save-cat":
                if not cat_name: raise ValueError("Nome da categoria obrigatório")
                
                # Conversão explícita para inteiro ou None
                parent_id_int = int(cat_parent) if cat_parent else None
                
                payload = CategoryCreate(
                    name=cat_name,
                    transaction_type=cat_type, # ENUM String (INCOME/EXPENSE)
                    color=cat_color,
                    parent_id=parent_id_int
                )
                CategoryService(db).create_category(user_id, payload)
                msg = f"Categoria '{cat_name}' criada!"

            elif trigger == "btn-save-acc":
                if not acc_name: raise ValueError("Nome da conta obrigatório")
                payload = AccountCreate(
                    name=acc_name,
                    account_type=AccountType(acc_type),
                    initial_balance=float(acc_balance or 0),
                    color="#2ecc71"
                )
                AccountService(db).create_account(user_id, payload)
                msg = f"Conta '{acc_name}' criada!"

            elif trigger == "btn-save-card":
                if not card_name: raise ValueError("Apelido do cartão obrigatório")
                payload = AccountCreate(
                    name=card_name,
                    account_type=AccountType.CREDIT_CARD,
                    initial_balance=0, # Cartão começa com saldo 0 (fatura zerada)
                    credit_limit=float(card_limit or 0),
                    closing_day=int(card_close),
                    due_day=int(card_due),
                    color="#f1c40f"
                )
                AccountService(db).create_account(user_id, payload)
                msg = f"Cartão '{card_name}' criado!"

        # Retorna um Toast de sucesso e incrementa o trigger para recarregar a lista
        toast = dbc.Toast(msg, header="Sucesso", color="success", duration=4000, icon="success", style={"position": "fixed", "top": 20, "right": 20, "zIndex": 9999})
        return (btn_cat or 0) + (btn_acc or 0) + (btn_card or 0), toast

    except Exception as e:
        app_logger.error(f"Erro ao salvar configuração: {e}")
        toast = dbc.Toast(f"Erro: {str(e)}", header="Erro", color="danger", duration=5000, icon="danger", style={"position": "fixed", "top": 20, "right": 20, "zIndex": 9999})
        return no_update, toast