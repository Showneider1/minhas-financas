"""
Callbacks de lançamentos financeiros (criar, editar, deletar).
"""
from dash import Input, Output, State, ctx, no_update
from datetime import date
import dash_bootstrap_components as dbc
from app import app
from database.connection import get_db_session
from services.finance_service import FinanceService
from services.category_service import CategoryService
from services.account_service import AccountService
from schemas.transaction_schema import TransactionCreate
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
    Output("modal-novo-lancamento",    "is_open",  allow_duplicate=True),
    Output("store-transacao-id-editar","data",     allow_duplicate=True),
    Output("data-pagamento",           "disabled"),
    Input("btn-novo-lancamento",  "n_clicks"),
    Input("btn-cancelar-modal",   "n_clicks"),
    Input("btn-salvar-lancamento","n_clicks"),
    Input("switch-pago",          "value"),
    State("modal-novo-lancamento","is_open"),
    prevent_initial_call=True,
)
def toggle_modal(n_novo, n_cancelar, n_salvar, switch_pago, is_open):
    if not ctx.triggered:
        return no_update, no_update, no_update

    trigger_id = ctx.triggered_id
    disable_date = not switch_pago

    if trigger_id == "switch-pago":
        return no_update, no_update, disable_date

    if trigger_id == "btn-novo-lancamento":
        if not n_novo:
            return no_update, no_update, no_update
        return True, None, disable_date

    if trigger_id in ["btn-cancelar-modal", "btn-salvar-lancamento"]:
        return False, None, False

    return is_open, no_update, disable_date



# ==========================================
# 3. CARREGAR OPÇÕES (CATEGORIAS E CONTAS)
# ==========================================
@app.callback(
    Output("select-categoria", "options"),
    Output("select-conta",     "options"),
    Input("tipo-lancamento",            "value"),
    Input("store-user-id",              "data"),
    Input("modal-novo-lancamento",      "is_open"),
    prevent_initial_call=True,
)
def carregar_opcoes(tipo, user_id, is_open):
    if not is_open or not user_id:
        return no_update, no_update

    try:
        with get_db_session() as db:
            cat_service = CategoryService(db)
            cats = cat_service.get_available_categories(user_id, TransactionType(tipo))
            opt_cats = [{"label": f"{c.icon} {c.name}", "value": c.id} for c in cats]

            acc_service = AccountService(db)
            accs = acc_service.get_user_accounts(user_id)
            opt_accs = [{"label": a.name, "value": a.id} for a in accs]

            return opt_cats, opt_accs
    except Exception as e:
        app_logger.error(f"Erro ao carregar opções: {e}")
        return [], []



# ==========================================
# 4. PREENCHER FORMULÁRIO (CRIAR OU EDITAR)
# ==========================================
@app.callback(
    Output("input-valor",           "value"),
    Output("input-descricao",       "value"),
    Output("select-categoria",      "value"),
    Output("select-conta",          "value"),
    Output("tipo-lancamento",       "value"),
    Output("data-compra",           "date"),
    Output("data-vencimento",       "date"),
    Output("data-pagamento",        "date"),
    Output("switch-pago",           "value"),
    Output("check-recorrencia",     "value"),
    Output("input-parcela-atual",   "value"),
    Output("input-total-parcelas",  "value"),
    Output("modal-header-title",    "children"),
    Input("modal-novo-lancamento",  "is_open"),
    State("store-transacao-id-editar", "data"),
    State("store-user-id",             "data"),
    prevent_initial_call=True,
)
def preencher_formulario(is_open, edit_id, user_id):
    if not is_open:
        return (no_update,) * 13

    hoje = date.today()

    if not edit_id:
        return (
            "", "", None, None, "EXPENSE",
            hoje, hoje, hoje, True,
            [], 1, 1,
            "Novo Lançamento"
        )

    try:
        with get_db_session() as db:
            t = db.query(Transaction).filter(
                Transaction.id == edit_id,
                Transaction.user_id == user_id,
            ).first()

            if not t:
                return (no_update,) * 13

            tipo       = t.transaction_type.value
            pago       = True if t.paid_date else False
            valor_fmt  = f"{t.base_amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            recorrencia = ["recorrente"] if t.is_recurring else []

            return (
                valor_fmt, t.description, t.category_id, t.account_id, tipo,
                t.purchase_date, t.due_date, t.paid_date, pago,
                recorrencia, t.installment_number, t.total_installments,
                "Editar Lançamento"
            )
    except Exception as e:
        app_logger.error(f"Erro ao carregar lançamento para edição: {e}")
        return (no_update,) * 13



# ==========================================
# 5. SALVAR (CREATE / UPDATE)
# — DONO ÚNICO do store-reload-dashboard —
# ==========================================
@app.callback(
    Output("feedback-transacao",     "children"),
    Output("store-reload-dashboard", "data"),          # <-- SEM allow_duplicate
    Input("btn-salvar-lancamento",   "n_clicks"),
    State("store-user-id",            "data"),
    State("store-transacao-id-editar","data"),
    State("tipo-lancamento",          "value"),
    State("input-valor",              "value"),
    State("input-descricao",          "value"),
    State("select-categoria",         "value"),
    State("select-conta",             "value"),
    State("data-compra",              "date"),
    State("data-vencimento",          "date"),
    State("data-pagamento",           "date"),
    State("switch-pago",              "value"),
    State("check-recorrencia",        "value"),
    State("input-parcela-atual",      "value"),
    State("input-total-parcelas",     "value"),
    State("store-reload-dashboard",   "data"),
    prevent_initial_call=True,
)
def salvar_transacao(n_clicks, user_id, edit_id, tipo, valor, descricao,
                     cat_id, acc_id, d_compra, d_venc, d_pagto,
                     switch_pago, recorrencia, parc_atual, parc_total,
                     reload_counter):

    if not n_clicks:
        return no_update, no_update

    try:
        if not valor:
            raise ValueError("Valor é obrigatório")
        if not cat_id:
            raise ValueError("Selecione uma categoria")
        if not acc_id:
            raise ValueError("Selecione uma conta")
        if not d_compra or not d_venc:
            raise ValueError("Datas de Compra e Vencimento são obrigatórias")

        valor_str = str(valor).replace("R$", "").replace(" ", "").strip()
        if "," in valor_str:
            valor_limpo = valor_str.replace(".", "").replace(",", ".")
        else:
            valor_limpo = valor_str

        valor_float = float(valor_limpo)
        if valor_float <= 0:
            raise ValueError("Valor deve ser maior que zero")

        date_purchase = date.fromisoformat(d_compra)
        date_due      = date.fromisoformat(d_venc)

        if date_due < date_purchase:
            raise ValueError("Data de vencimento não pode ser anterior à data de compra")

        date_paid = None
        if switch_pago:
            date_paid = date.fromisoformat(d_pagto) if d_pagto else date_due

        is_recorrente = True if "recorrente" in (recorrencia or []) else False

        payload = TransactionCreate(
            description=descricao.strip() if descricao else "Sem descrição",
            base_amount=valor_float,
            transaction_type=TransactionType(tipo),
            category_id=int(cat_id),
            account_id=int(acc_id),
            purchase_date=date_purchase,
            due_date=date_due,
            paid_date=date_paid,
            is_recurring=is_recorrente,
            installment_number=int(parc_atual or 1),
            total_installments=int(parc_total or 1),
            notes="",
        )

        with get_db_session() as db:
            finance_service = FinanceService(db)
            if edit_id:
                finance_service.update_transaction(edit_id, user_id, payload)
                msg = "✅ Lançamento atualizado com sucesso!"
            else:
                finance_service.create_transaction(user_id, payload)
                msg = "✅ Lançamento criado com sucesso!"

        return dbc.Alert(msg, color="success", duration=3000), (reload_counter or 0) + 1

    except ValueError as e:
        return dbc.Alert(f"⚠️ {str(e)}", color="warning", duration=4000), no_update

    except Exception as e:
        app_logger.error(f"Erro ao salvar transação: {e}")
        import traceback
        traceback.print_exc()
        return dbc.Alert(f"❌ Erro inesperado: {str(e)}", color="danger", duration=5000), no_update