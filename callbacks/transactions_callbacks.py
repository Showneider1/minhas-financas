from dash import Input, Output, State, callback_context, no_update
from datetime import date
import dash_bootstrap_components as dbc
from app import app
from database.connection import get_db_session
from services.finance_service import FinanceService
from services.category_service import CategoryService
from database.models.category import TransactionType
from database.models.transaction import Transaction
from config.logging_config import app_logger

# ==========================================
# 1. SEGURANÇA: FECHA MODAL NA NAVEGAÇÃO
# ==========================================
@app.callback(
    Output("modal-novo-lancamento", "is_open"),
    Input("url", "pathname"),
    prevent_initial_call=True,
)
def resetar_modal_ao_mudar_pagina(pathname):
    return False

# ==========================================
# 2. CONTROLE DO MODAL (COM BLINDAGEM RESTAURADA)
# ==========================================
@app.callback(
    Output("modal-novo-lancamento", "is_open", allow_duplicate=True),
    Output("store-transacao-id-editar", "data", allow_duplicate=True),
    Input("btn-novo-lancamento", "n_clicks"),
    Input("btn-cancelar-modal", "n_clicks"),
    Input("btn-salvar-lancamento", "n_clicks"),
    State("modal-novo-lancamento", "is_open"),
    prevent_initial_call=True,
)
def toggle_modal(n_novo, n_cancelar, n_salvar, is_open):
    ctx = callback_context
    if not ctx.triggered: return no_update
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    # --- AQUI ESTAVA O PROBLEMA ---
    if trigger_id == "btn-novo-lancamento":
        # Se n_novo for None ou 0 (inicialização), IGNORA.
        if not n_novo: 
            return no_update, no_update
        
        # Se foi um clique real, abre o modal e limpa o ID de edição
        return True, None 
    
    if trigger_id in ["btn-cancelar-modal", "btn-salvar-lancamento"]:
        return False, None # Fecha e limpa
    
    return is_open, no_update

# ==========================================
# 3. CARREGA CATEGORIAS
# ==========================================
@app.callback(
    Output("select-categoria", "options"),
    Input("tipo-lancamento", "value"),
    Input("store-user-id", "data"),
    Input("modal-novo-lancamento", "is_open"),
    prevent_initial_call=True,
)
def carregar_categorias_por_tipo(tipo, user_id, is_open):
    if not is_open: return no_update
    if not user_id or not tipo: return []
    
    try:
        with get_db_session() as db:
            category_service = CategoryService(db)
            categories = category_service.get_available_categories(user_id, TransactionType(tipo))
            return [{"label": f"{cat.icon or '📁'} {cat.name}", "value": cat.id} for cat in categories]
    except Exception as e:
        app_logger.error(f"Erro categorias: {e}")
        return []

# ==========================================
# 4. CARREGA CONTAS
# ==========================================
@app.callback(
    Output("select-conta", "options"),
    Input("store-user-id", "data"),
    Input("modal-novo-lancamento", "is_open"),
    prevent_initial_call=True,
)
def carregar_contas(user_id, is_open):
    if not is_open: return no_update
    if not user_id: return []
    
    try:
        with get_db_session() as db:
            from services.account_service import AccountService
            account_service = AccountService(db)
            accounts = account_service.get_user_accounts(user_id)
            return [{"label": acc.name, "value": acc.id} for acc in accounts]
    except Exception as e:
        app_logger.error(f"Erro contas: {e}")
        return []

# ==========================================
# 5. PREENCHER FORMULÁRIO (CRIAR OU EDITAR)
# ==========================================
@app.callback(
    Output("input-valor", "value"),
    Output("input-descricao", "value"),
    Output("select-categoria", "value"),
    Output("select-conta", "value"),
    Output("data-lancamento", "date"),
    Output("switch-pago", "value"),
    Output("tipo-lancamento", "value"),
    Output("modal-header-title", "children"),
    Input("modal-novo-lancamento", "is_open"),
    State("store-transacao-id-editar", "data"),
    State("store-user-id", "data"),
    prevent_initial_call=True,
)
def preencher_formulario(is_open, edit_id, user_id):
    if not is_open: return no_update
    
    # MODO CRIAÇÃO
    if not edit_id:
        return "", "", None, None, date.today(), False, "EXPENSE", "Novo Lançamento"
    
    # MODO EDIÇÃO
    try:
        with get_db_session() as db:
            t = db.query(Transaction).filter(Transaction.id == edit_id, Transaction.user_id == user_id).first()
            if not t: return "", "", None, None, date.today(), False, "EXPENSE", "Erro"
            
            tipo = "INCOME" if t.transaction_type.value == "INCOME" else "EXPENSE"
            pago = True if t.paid_date else False
            data_show = t.paid_date if t.paid_date else t.due_date
            valor_formatado = f"{t.base_amount:.2f}".replace(".", ",")
            
            return valor_formatado, t.description, t.category_id, t.account_id, data_show, pago, tipo, "Editar Lançamento"
    except Exception:
        return no_update

# ==========================================
# 6. SALVAR TRANSAÇÃO
# ==========================================
@app.callback(
    Output("feedback-transacao", "children"),
    Output("store-reload-dashboard", "data", allow_duplicate=True),
    Input("btn-salvar-lancamento", "n_clicks"),
    State("store-user-id", "data"),
    State("store-transacao-id-editar", "data"),
    State("tipo-lancamento", "value"),
    State("input-valor", "value"),
    State("input-descricao", "value"),
    State("select-categoria", "value"),
    State("select-conta", "value"),
    State("data-lancamento", "date"),
    State("switch-pago", "value"),
    prevent_initial_call=True,
)
def salvar_transacao(n_clicks, user_id, edit_id, tipo, valor, descricao, categoria_id, conta_id, data_lancamento, pago):
    if not n_clicks: return no_update
    
    try:
        valor_limpo = str(valor).replace(".", "").replace(",", ".").replace("R$", "").strip()
        valor_float = float(valor_limpo)
        if valor_float <= 0: return dbc.Alert("Valor inválido", color="danger"), no_update

        if data_lancamento: due_date = date.fromisoformat(data_lancamento)
        else: due_date = date.today()
        paid_date = due_date if pago else None
        
        from schemas.transaction_schema import TransactionCreate
        data = TransactionCreate(
            description=descricao or "Sem descrição",
            base_amount=valor_float,
            transaction_type=TransactionType(tipo),
            category_id=categoria_id,
            account_id=conta_id,
            due_date=due_date,
            paid_date=paid_date,
        )
        
        with get_db_session() as db:
            finance_service = FinanceService(db)
            if edit_id:
                finance_service.update_transaction(edit_id, user_id, data)
                msg = "✅ Atualizado com sucesso!"
            else:
                finance_service.create_transaction(user_id, data)
                msg = "✅ Criado com sucesso!"
        
        return dbc.Alert(msg, color="success", duration=3000), True
        
    except Exception as e:
        app_logger.error(f"Erro salvar: {e}")
        return dbc.Alert(f"Erro: {e}", color="danger"), no_update