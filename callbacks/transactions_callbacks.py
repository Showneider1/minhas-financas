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
# 1. SEGURANÇA NA NAVEGAÇÃO
# ==========================================
@app.callback(
    Output("modal-novo-lancamento", "is_open"),
    Input("url", "pathname"),
    prevent_initial_call=True,
)
def resetar_modal_ao_mudar_pagina(pathname):
    return False

# ==========================================
# 2. CONTROLE VISUAL (ABRIR/FECHAR MODAL)
# ==========================================
@app.callback(
    Output("modal-novo-lancamento", "is_open", allow_duplicate=True),
    Output("store-transacao-id-editar", "data", allow_duplicate=True),
    # Controla visibilidade da Data de Pagamento
    Output("data-pagamento", "disabled"), 
    
    Input("btn-novo-lancamento", "n_clicks"),
    Input("btn-cancelar-modal", "n_clicks"),
    Input("btn-salvar-lancamento", "n_clicks"),
    Input("switch-pago", "value"),
    State("modal-novo-lancamento", "is_open"),
    prevent_initial_call=True,
)
def toggle_modal(n_novo, n_cancelar, n_salvar, switch_pago, is_open):
    ctx = callback_context
    if not ctx.triggered: return no_update
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    # Lógica de desabilitar data de pagamento
    disable_date = not switch_pago 

    if trigger_id == "switch-pago":
        return no_update, no_update, disable_date

    if trigger_id == "btn-novo-lancamento":
        if not n_novo: return no_update, no_update, no_update
        return True, None, disable_date
    
    if trigger_id in ["btn-cancelar-modal", "btn-salvar-lancamento"]:
        return False, None, no_update
    
    return is_open, no_update, disable_date

# ==========================================
# 3. CARREGAR OPÇÕES (CATEGORIAS E CONTAS)
# ==========================================
@app.callback(
    Output("select-categoria", "options"),
    Output("select-conta", "options"),
    Input("tipo-lancamento", "value"),
    Input("store-user-id", "data"),
    Input("modal-novo-lancamento", "is_open"),
    prevent_initial_call=True,
)
def carregar_opcoes(tipo, user_id, is_open):
    if not is_open or not user_id: return no_update, no_update
    
    try:
        with get_db_session() as db:
            # Categorias
            cat_service = CategoryService(db)
            cats = cat_service.get_available_categories(user_id, TransactionType(tipo))
            opt_cats = [{"label": f"{c.icon} {c.name}", "value": c.id} for c in cats]
            
            # Contas
            from services.account_service import AccountService
            acc_service = AccountService(db)
            accs = acc_service.get_user_accounts(user_id)
            opt_accs = [{"label": a.name, "value": a.id} for a in accs]
            
            return opt_cats, opt_accs
    except Exception as e:
        app_logger.error(f"Erro opções: {e}")
        return [], []

# ==========================================
# 4. PREENCHER FORMULÁRIO (CRIAR OU EDITAR)
# ==========================================
@app.callback(
    Output("input-valor", "value"),
    Output("input-descricao", "value"),
    Output("select-categoria", "value"),
    Output("select-conta", "value"),
    Output("tipo-lancamento", "value"),
    
    # Novas Datas
    Output("data-compra", "date"),
    Output("data-vencimento", "date"),
    Output("data-pagamento", "date"),
    Output("switch-pago", "value"),
    
    # Parcelas
    Output("check-recorrencia", "value"),
    Output("input-parcela-atual", "value"),
    Output("input-total-parcelas", "value"),
    Output("modal-header-title", "children"),
    
    Input("modal-novo-lancamento", "is_open"),
    State("store-transacao-id-editar", "data"),
    State("store-user-id", "data"),
    prevent_initial_call=True,
)
def preencher_formulario(is_open, edit_id, user_id):
    if not is_open: return no_update
    
    hoje = date.today()
    
    # --- MODO CRIAÇÃO (LIMPAR CAMPOS) ---
    if not edit_id:
        return (
            "", "", None, None, "EXPENSE", 
            hoje, hoje, hoje, True, # Datas padrão: Hoje e Switch Pago=True
            [], 1, 1, # Parcelas padrão
            "Novo Lançamento"
        )
    
    # --- MODO EDIÇÃO (CARREGAR DO BANCO) ---
    try:
        with get_db_session() as db:
            t = db.query(Transaction).filter(Transaction.id == edit_id, Transaction.user_id == user_id).first()
            if not t: return no_update
            
            tipo = t.transaction_type.value
            pago = True if t.paid_date else False
            valor_fmt = f"{t.base_amount:.2f}".replace(".", ",")
            
            recorrencia = ["recorrente"] if t.is_recurring else []
            
            return (
                valor_fmt, t.description, t.category_id, t.account_id, tipo,
                t.purchase_date, t.due_date, t.paid_date, pago,
                recorrencia, t.installment_number, t.total_installments,
                "Editar Lançamento"
            )
    except Exception as e:
        app_logger.error(f"Erro ao carregar edição: {e}")
        return no_update

# ==========================================
# 5. SALVAR (CREATE / UPDATE)
# ==========================================
@app.callback(
    Output("feedback-transacao", "children"),
    Output("store-reload-dashboard", "data", allow_duplicate=True),
    Input("btn-salvar-lancamento", "n_clicks"),
    
    State("store-user-id", "data"),
    State("store-transacao-id-editar", "data"),
    
    # Inputs Básicos
    State("tipo-lancamento", "value"),
    State("input-valor", "value"),
    State("input-descricao", "value"),
    State("select-categoria", "value"),
    State("select-conta", "value"),
    
    # Inputs Datas
    State("data-compra", "date"),
    State("data-vencimento", "date"),
    State("data-pagamento", "date"),
    State("switch-pago", "value"),
    
    # Inputs Parcelas
    State("check-recorrencia", "value"),
    State("input-parcela-atual", "value"),
    State("input-total-parcelas", "value"),
    
    prevent_initial_call=True,
)
def salvar_transacao(n_clicks, user_id, edit_id, tipo, valor, descricao, 
                     cat_id, acc_id, d_compra, d_venc, d_pagto, 
                     switch_pago, recorrencia, parc_atual, parc_total):
    
    if not n_clicks: return no_update
    
    try:
        # 1. Tratamento do Valor
        if not valor: raise ValueError("Valor é obrigatório")
        valor_limpo = str(valor).replace(".", "").replace(",", ".").replace("R$", "").strip()
        valor_float = float(valor_limpo)
        if valor_float <= 0: raise ValueError("Valor deve ser positivo")

        # 2. Tratamento de Datas
        if not d_compra or not d_venc: raise ValueError("Datas de Compra e Vencimento são obrigatórias")
        
        date_purchase = date.fromisoformat(d_compra)
        date_due = date.fromisoformat(d_venc)
        
        # Se Switch Pago for False, paid_date é None. Se True, usa a data informada (ou Vencimento como fallback)
        date_paid = None
        if switch_pago:
            date_paid = date.fromisoformat(d_pagto) if d_pagto else date_due

        # 3. Montar Objeto Schema
        from schemas.transaction_schema import TransactionCreate
        from database.models.category import TransactionType

        is_recorrente = True if "recorrente" in (recorrencia or []) else False

        payload = TransactionCreate(
            description=descricao or "Sem descrição",
            base_amount=valor_float,
            transaction_type=TransactionType(tipo),
            category_id=int(cat_id),
            account_id=int(acc_id),
            
            # Novos campos robustos
            purchase_date=date_purchase,
            due_date=date_due,
            paid_date=date_paid,
            
            is_recurring=is_recorrente,
            installment_number=int(parc_atual or 1),
            total_installments=int(parc_total or 1),
            notes=""
        )
        
        # 4. Salvar no Banco
        with get_db_session() as db:
            finance_service = FinanceService(db)
            if edit_id:
                finance_service.update_transaction(edit_id, user_id, payload)
                msg = "✅ Atualizado com sucesso!"
            else:
                finance_service.create_transaction(user_id, payload)
                msg = "✅ Criado com sucesso!"
        
        return dbc.Alert(msg, color="success", duration=3000), True
        
    except Exception as e:
        app_logger.error(f"Erro salvar: {e}")
        return dbc.Alert(f"Erro: {str(e)}", color="danger"), no_update