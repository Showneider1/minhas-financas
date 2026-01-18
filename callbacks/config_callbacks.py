"""
Callbacks da página de configurações (categorias e contas).
"""
from dash import Input, Output, State, callback_context, no_update
import dash_bootstrap_components as dbc
from dash import html
from app import app
from database.connection import get_db_session
from services.category_service import CategoryService
from services.account_service import AccountService
from schemas.category_schema import CategoryCreate
from schemas.account_schema import AccountCreate
from database.models.category import TransactionType
from database.models.account import AccountType
from sqlalchemy import text


# ==========================================
# CALLBACKS DE CATEGORIAS
# ==========================================

@app.callback(
    Output("modal-categoria", "is_open"),
    Output("select-categoria-pai", "options"),
    Input("btn-nova-categoria", "n_clicks"),
    Input("btn-cancelar-categoria", "n_clicks"),
    Input("btn-salvar-categoria", "n_clicks"),
    State("modal-categoria", "is_open"),
    State("store-user-id", "data"),
    prevent_initial_call=True,
)
def toggle_modal_categoria(open_click, cancel_click, save_click, is_open, user_id):
    """Abre/fecha modal de categoria e carrega lista de categorias principais."""
    ctx = callback_context
    if not ctx.triggered:
        return no_update, no_update
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if trigger_id == "btn-nova-categoria":
        # Carrega categorias principais para o select
        try:
            if user_id:
                with get_db_session() as db:
                    category_service = CategoryService(db)
                    categories = category_service.get_user_categories(user_id)
                    
                    # Filtra apenas categorias principais (sem parent)
                    main_categories = [cat for cat in categories if cat.parent_id is None]
                    
                    options = [{"label": "Nenhuma (criar categoria principal)", "value": ""}]
                    options.extend([
                        {"label": f"{cat.icon or '📁'} {cat.name}", "value": cat.id}
                        for cat in main_categories
                    ])
                    
                    return True, options
        except:
            pass
        
        return True, [{"label": "Nenhuma (criar categoria principal)", "value": ""}]
    
    elif trigger_id in ["btn-cancelar-categoria", "btn-salvar-categoria"]:
        return False, no_update
    
    return no_update, no_update


@app.callback(
    Output("feedback-categorias", "children"),
    Output("lista-categorias", "children"),
    Input("btn-salvar-categoria", "n_clicks"),
    Input("tabs-configuracoes", "active_tab"),
    State("store-user-id", "data"),
    State("input-categoria-nome", "value"),
    State("select-categoria-pai", "value"),
    prevent_initial_call=True,
)
def gerenciar_categorias(n_clicks, active_tab, user_id, nome, parent_id):
    """Salva categoria e atualiza lista."""
    ctx = callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    feedback = None
    
    # Se clicou em salvar
    if trigger_id == "btn-salvar-categoria" and n_clicks and user_id:
        try:
            if not nome:
                feedback = dbc.Alert("Preencha o nome", color="warning", duration=3000)
            else:
                print(f"Criando categoria: {nome} - Parent: {parent_id}")
                
                # Cria categoria usando text()
                with get_db_session() as db:
                    db.execute(
                        text("""
                            INSERT INTO categories (name, icon, color, user_id, parent_id, is_system)
                            VALUES (:name, :icon, :color, :user_id, :parent_id, :is_system)
                        """),
                        {
                            "name": nome,
                            "icon": "📁",
                            "color": "#3498db",
                            "user_id": user_id,
                            "parent_id": int(parent_id) if parent_id else None,
                            "is_system": False,
                        }
                    )
                
                feedback = dbc.Alert("Categoria criada!", color="success", duration=3000)
        
        except Exception as e:
            print(f"Erro ao criar categoria: {e}")
            import traceback
            traceback.print_exc()
            feedback = dbc.Alert(f"Erro: {e}", color="danger", duration=4000)
    
    # Carrega lista de categorias
    if user_id and active_tab == "tab-categorias":
        try:
            with get_db_session() as db:
                # Query usando text()
                result = db.execute(
                    text("""
                        SELECT 
                            c.id, c.name, c.icon, c.parent_id, c.is_system,
                            p.name as parent_name
                        FROM categories c
                        LEFT JOIN categories p ON c.parent_id = p.id
                        WHERE c.user_id = :user_id OR c.is_system = 1
                        ORDER BY COALESCE(c.parent_id, c.id), c.parent_id IS NULL DESC, c.name
                    """),
                    {"user_id": user_id}
                )
                categories = result.fetchall()
            
            if not categories:
                lista = html.P("Nenhuma categoria cadastrada", className="text-muted mt-3")
            else:
                items = []
                for cat in categories:
                    # Indica se é subcategoria
                    indent = "  ↳ " if cat.parent_id else ""
                    sistema_badge = dbc.Badge("Sistema", color="secondary", className="ms-2") if cat.is_system else None
                    
                    items.append(
                        dbc.ListGroupItem([
                            html.Span(f"{indent}{cat.icon or '📁'}", className="me-2"),
                            html.Strong(cat.name),
                            sistema_badge if sistema_badge else html.Span(),
                        ])
                    )
                
                lista = dbc.ListGroup(items, className="mt-3")
        
        except Exception as e:
            print(f"Erro ao carregar categorias: {e}")
            import traceback
            traceback.print_exc()
            lista = html.P(f"Erro ao carregar: {e}", className="text-danger")
    else:
        lista = no_update
    
    return feedback, lista


# ==========================================
# CALLBACKS DE CONTAS
# ==========================================

@app.callback(
    Output("modal-conta", "is_open"),
    Input("btn-nova-conta", "n_clicks"),
    Input("btn-cancelar-conta", "n_clicks"),
    Input("btn-salvar-conta", "n_clicks"),
    State("modal-conta", "is_open"),
    prevent_initial_call=True,
)
def toggle_modal_conta(open_click, cancel_click, save_click, is_open):
    """Abre/fecha modal de conta."""
    ctx = callback_context
    if not ctx.triggered:
        return no_update
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if trigger_id == "btn-nova-conta":
        return True
    elif trigger_id in ["btn-cancelar-conta", "btn-salvar-conta"]:
        return False
    
    return no_update


@app.callback(
    Output("feedback-contas", "children"),
    Output("lista-contas", "children"),
    Input("btn-salvar-conta", "n_clicks"),
    Input("tabs-configuracoes", "active_tab"),
    State("store-user-id", "data"),
    State("input-conta-nome", "value"),
    State("input-conta-tipo", "value"),
    State("input-conta-saldo", "value"),
    prevent_initial_call=True,
)
def gerenciar_contas(n_clicks, active_tab, user_id, nome, tipo, saldo):
    """Salva conta e atualiza lista."""
    ctx = callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    feedback = None
    
    if trigger_id == "btn-salvar-conta" and n_clicks and user_id:
        try:
            if not nome:
                feedback = dbc.Alert("Preencha o nome", color="warning", duration=3000)
            else:
                try:
                    saldo_limpo = str(saldo).replace(".", "").replace(",", ".").replace("R$", "").strip()
                    saldo_float = float(saldo_limpo)
                except:
                    saldo_float = 0.0
                
                data = AccountCreate(
                    name=nome,
                    account_type=AccountType[tipo],
                    initial_balance=saldo_float,
                    color="#2ecc71",
                )
                
                with get_db_session() as db:
                    account_service = AccountService(db)
                    account_service.create_account(user_id, data)
                
                feedback = dbc.Alert("Conta criada!", color="success", duration=3000)
        
        except Exception as e:
            print(f"Erro ao criar conta: {e}")
            import traceback
            traceback.print_exc()
            feedback = dbc.Alert(f"Erro: {e}", color="danger", duration=4000)
    
    # Carrega lista de contas
    if user_id and active_tab == "tab-contas":
        try:
            with get_db_session() as db:
                account_service = AccountService(db)
                accounts = account_service.get_user_accounts(user_id)
                
                # CONVERTE PARA DICT DENTRO DA SESSÃO
                accounts_data = [
                    {
                        "id": acc.id,
                        "name": acc.name,
                        "balance": acc.balance,
                        "account_type": acc.account_type.value,
                    }
                    for acc in accounts
                ]
            
            # USA OS DADOS FORA DA SESSÃO
            if not accounts_data:
                lista = html.P("Nenhuma conta cadastrada", className="text-muted mt-3")
            else:
                items = []
                for acc in accounts_data:
                    saldo_badge = dbc.Badge(
                        f"R$ {acc['balance']:,.2f}",
                        color="success" if acc['balance'] >= 0 else "danger",
                        className="ms-2",
                    )
                    
                    items.append(
                        dbc.ListGroupItem([
                            html.Strong(acc['name']),
                            saldo_badge,
                            html.Small(f" • {acc['account_type']}", className="text-muted ms-2"),
                        ])
                    )
                
                lista = dbc.ListGroup(items, className="mt-3")
        
        except Exception as e:
            print(f"Erro ao carregar contas: {e}")
            import traceback
            traceback.print_exc()
            lista = html.P(f"Erro ao carregar: {e}", className="text-danger")
    else:
        lista = no_update
    
    return feedback, lista
