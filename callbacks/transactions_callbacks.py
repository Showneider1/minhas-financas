"""
Callbacks para gerenciamento de transações.
SOLUÇÃO FINAL: 
1. Reseta modal ao mudar de página (URL).
2. Controla abertura apenas por clique nos botões.
"""
from dash import Input, Output, State, callback_context, no_update
from datetime import date
import dash_bootstrap_components as dbc
from app import app
from database.connection import get_db_session
from services.finance_service import FinanceService
from services.category_service import CategoryService
from database.models.category import TransactionType
from config.logging_config import app_logger
from dash import dcc

# ==========================================
# 1. SEGURANÇA: FECHA MODAL NA NAVEGAÇÃO
# ==========================================
@app.callback(
    Output("modal-novo-lancamento", "is_open"),
    Input("url", "pathname"),
    prevent_initial_call=True,
)
def resetar_modal_ao_mudar_pagina(pathname):
    # Força o fechamento sempre que a URL mudar
    return False

# ==========================================
# 2. CONTROLE DO MODAL (COM BLINDAGEM)
# ==========================================
@app.callback(
    Output("modal-novo-lancamento", "is_open", allow_duplicate=True),
    Input("btn-novo-lancamento", "n_clicks"),
    Input("btn-cancelar-modal", "n_clicks"),
    Input("btn-salvar-lancamento", "n_clicks"),
    State("modal-novo-lancamento", "is_open"),
    prevent_initial_call=True,
)
def toggle_modal(n_novo, n_cancelar, n_salvar, is_open):
    ctx = callback_context

    # Se não houve gatilho real, não faz nada
    if not ctx.triggered:
        return no_update
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    # --- AQUI ESTÁ A CORREÇÃO (BLINDAGEM) ---
    # Se o gatilho for o botão "Novo", verificamos se ele tem cliques reais.
    # Quando a página recarrega, o n_clicks pode ser 0 ou None.
    if trigger_id == "btn-novo-lancamento":
        if not n_novo or n_novo == 0:
            return no_update # Ignora clique zero (inicialização do botão)
        return True # Abre o modal

    # Fecha ao clicar em Cancelar ou Salvar
    if trigger_id in ["btn-cancelar-modal", "btn-salvar-lancamento"]:
        return False
    
    return is_open


# ==========================================
# CARREGA CATEGORIAS
# ==========================================
@app.callback(
    Output("select-categoria", "options"),
    Input("tipo-lancamento", "value"),
    Input("store-user-id", "data"),
    prevent_initial_call=True,
)
def carregar_categorias_por_tipo(tipo, user_id):
    """
    Carrega categorias filtradas por tipo de transação.
    """
    try:
        if not user_id or not tipo:
            return []
        
        transaction_type = TransactionType(tipo)
        
        with get_db_session() as db:
            category_service = CategoryService(db)
            categories = category_service.get_available_categories(
                user_id, transaction_type
            )
            
            return [
                {
                    "label": f"{cat.icon or '📁'} {cat.name}",
                    "value": cat.id
                }
                for cat in categories
            ]
        
    except Exception as e:
        app_logger.error(f"Erro ao carregar categorias: {e}")
        return []


# ==========================================
# CARREGA CONTAS
# ==========================================
@app.callback(
    Output("select-conta", "options"),
    Input("store-user-id", "data"),
    prevent_initial_call=True,
)
def carregar_contas(user_id):
    """
    Carrega contas do usuário.
    """
    try:
        if not user_id:
            return []
        
        with get_db_session() as db:
            from services.account_service import AccountService
            account_service = AccountService(db)
            accounts = account_service.get_user_accounts(user_id)
            
            return [
                {"label": acc.name, "value": acc.id}
                for acc in accounts
            ]
        
    except Exception as e:
        app_logger.error(f"Erro ao carregar contas: {e}")
        return []


# ==========================================
# LIMPAR FORMULÁRIO AO FECHAR MODAL
# ==========================================
@app.callback(
    Output("input-valor", "value"),
    Output("input-descricao", "value"),
    Output("select-categoria", "value"),
    Output("select-conta", "value"),
    Output("data-lancamento", "date"),
    Output("switch-pago", "value"),
    Output("tipo-lancamento", "value"),
    Input("modal-novo-lancamento", "is_open"),
    prevent_initial_call=True,
)
def limpar_formulario(is_open):
    """
    Reseta formulário quando modal fecha.
    """
    if not is_open:
        return "", "", None, None, date.today(), False, "EXPENSE"
    return no_update, no_update, no_update, no_update, no_update, no_update, no_update


# ==========================================
# SALVAR TRANSAÇÃO
# ==========================================
@app.callback(
    Output("feedback-transacao", "children"),
    Output("store-reload-dashboard", "data"),
    Input("btn-salvar-lancamento", "n_clicks"),
    State("store-user-id", "data"),
    State("tipo-lancamento", "value"),
    State("input-valor", "value"),
    State("input-descricao", "value"),
    State("select-categoria", "value"),
    State("select-conta", "value"),
    State("data-lancamento", "date"),
    State("switch-pago", "value"),
    prevent_initial_call=True,
)
def salvar_transacao(
    n_clicks,
    user_id,
    tipo,
    valor,
    descricao,
    categoria_id,
    conta_id,
    data_lancamento,
    pago,
):
    """
    Salva nova transação com validações.
    """
    try:
        if not user_id or not n_clicks:
            return no_update, no_update
        
        # Validações básicas
        if not valor or not categoria_id or not conta_id:
            return dbc.Alert(
                "Preencha todos os campos obrigatórios",
                color="warning",
                duration=4000,
                dismissable=True,
            ), no_update
        
        # Converte valor
        try:
            valor_limpo = str(valor).replace(".", "").replace(",", ".").replace("R$", "").strip()
            valor_float = float(valor_limpo)
        except Exception as e:
            app_logger.error(f"Erro ao converter valor: {e}")
            return dbc.Alert(
                "Valor inválido",
                color="danger",
                duration=4000,
                dismissable=True,
            ), no_update
        
        if valor_float <= 0:
            return dbc.Alert(
                "Valor deve ser maior que zero",
                color="danger",
                duration=4000,
                dismissable=True,
            ), no_update
        
        # Prepara data
        if data_lancamento:
            due_date = date.fromisoformat(data_lancamento)
        else:
            due_date = date.today()
        
        paid_date = due_date if pago else None
        
        # Cria schema
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
        
        # Salva no banco
        with get_db_session() as db:
            finance_service = FinanceService(db)
            transaction = finance_service.create_transaction(user_id, data)
            app_logger.info(f"✅ Transação criada! ID: {transaction.id}")
        
        return dbc.Alert(
            "✅ Transação salva com sucesso!",
            color="success",
            duration=3000,
            dismissable=True,
        ), n_clicks
        
    except Exception as e:
        app_logger.error(f"❌ Erro ao salvar transação: {e}")
        import traceback
        traceback.print_exc()
        
        return dbc.Alert(
            f"❌ Erro: {str(e)}",
            color="danger",
            duration=4000,
            dismissable=True,
        ), no_update