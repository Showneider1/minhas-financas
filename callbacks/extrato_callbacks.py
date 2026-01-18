from dash import Input, Output, State, no_update, ctx
from app import app
from database.connection import get_db_session
from database.models.transaction import Transaction
from datetime import datetime

# ==========================================
# 1. POPULAR TABELA (Sem alterações)
# ==========================================
@app.callback(
    Output("grid-transacoes", "rowData"),
    Input("extrato-periodo", "start_date"),
    Input("extrato-periodo", "end_date"),
    Input("store-reload-dashboard", "data"),
    State("store-user-id", "data"),
)
def atualizar_extrato(start_date, end_date, reload, user_id):
    if not user_id: return []
    try:
        if not start_date: start_date = datetime.now().replace(day=1).isoformat()
        if not end_date: end_date = datetime.now().isoformat()
        d_inicio = datetime.fromisoformat(start_date)
        d_fim = datetime.fromisoformat(end_date)

        with get_db_session() as db:
            transacoes = db.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.paid_date >= d_inicio,
                Transaction.paid_date <= d_fim
            ).order_by(Transaction.paid_date.desc()).all()
            
            data = []
            for t in transacoes:
                data.append({
                    "data": t.paid_date.strftime("%d/%m/%Y") if t.paid_date else t.due_date.strftime("%d/%m/%Y"),
                    "descricao": t.description,
                    "categoria": f"{t.category.icon or ''} {t.category.name}" if t.category else "-",
                    "conta": t.account.name if t.account else "-",
                    "valor": t.base_amount,
                    "tipo": "Receita" if t.transaction_type.value == "INCOME" else "Despesa",
                    "status": "Pago" if t.paid_date else "Pendente",
                    "editar": t.id,  
                    "excluir": t.id
                })
            return data
    except Exception as e:
        print(f"Erro extrato: {e}")
        return []

# ==========================================
# 2. INTERAÇÃO COM A TABELA (CORREÇÃO AQUI)
# ==========================================
@app.callback(
    # --- ADICIONEI allow_duplicate=True NESTES DOIS ---
    Output("store-transacao-id-editar", "data", allow_duplicate=True), 
    Output("modal-novo-lancamento", "is_open", allow_duplicate=True),
    # --------------------------------------------------
    Output("store-id-exclusao", "data"),
    Output("modal-confirmacao-exclusao", "is_open"),
    Input("grid-transacoes", "cellClicked"),
    prevent_initial_call=True
)
def interagir_tabela(cell_clicked):
    if not cell_clicked: return no_update, no_update, no_update, no_update
    
    col_id = cell_clicked.get("colId")
    valor_clicado = cell_clicked.get("value")
    
    if not valor_clicado: return no_update, no_update, no_update, no_update
    transacao_id = valor_clicado

    # --- CLIQUE NA LIXEIRA -> ABRE MODAL DE CONFIRMAÇÃO ---
    if col_id == "excluir":
        # Não deleta! Só abre o modal e guarda o ID
        return no_update, no_update, transacao_id, True

    # --- CLIQUE NO LÁPIS -> ABRE MODAL DE EDIÇÃO ---
    if col_id == "editar":
        return transacao_id, True, no_update, no_update

    return no_update, no_update, no_update, no_update

# ==========================================
# 3. CONFIRMAR EXCLUSÃO (Sem alterações)
# ==========================================
@app.callback(
    Output("store-reload-dashboard", "data", allow_duplicate=True),
    Output("modal-confirmacao-exclusao", "is_open", allow_duplicate=True),
    Input("btn-confirmar-exclusao", "n_clicks"),
    Input("btn-cancelar-exclusao", "n_clicks"),
    State("store-id-exclusao", "data"),
    State("store-user-id", "data"),
    prevent_initial_call=True
)
def executar_exclusao(n_confirmar, n_cancelar, transacao_id, user_id):
    trigger = ctx.triggered_id
    
    if trigger == "btn-cancelar-exclusao":
        return no_update, False
    
    if trigger == "btn-confirmar-exclusao" and transacao_id:
        try:
            with get_db_session() as db:
                t = db.query(Transaction).filter(Transaction.id == transacao_id, Transaction.user_id == user_id).first()
                if t:
                    db.delete(t)
            print(f"✅ ID {transacao_id} excluído definitivamente.")
            return True, False 
        except Exception as e:
            print(f"❌ Erro ao excluir: {e}")
            return no_update, False
            
    return no_update, no_update