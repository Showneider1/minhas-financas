"""
Callbacks do modal global de nova transação.

Suporta:
- Receita
- Despesa
- Transferência entre contas
"""

from datetime import date
from decimal import Decimal, InvalidOperation

import dash_bootstrap_components as dbc
from dash import Input, Output, State, ctx, no_update

from app import app
from config.logging_config import app_logger
from database.connection import get_db_session
from database.models.category import TransactionType
from database.models.transaction import Transaction
from middleware.auth_context import resolve_user
from schemas.transaction_schema import TransactionCreate, TransactionUpdate
from services.account_service import AccountService
from services.balance_service import BalanceService
from services.category_service import CategoryService
from services.finance_service import FinanceService
from services.transfer_service import TransferError, TransferService
from utils.exceptions import AuthenticationError


# ==========================================
# 1. SEGURANÇA NA NAVEGAÇÃO
# ==========================================
@app.callback(
    Output("modal-novo-lancamento", "is_open"),
    Input("url", "pathname"),
    prevent_initial_call=True,
)
def resetar_modal_ao_mudar_pagina(pathname):
    """Fecha o modal ao trocar de página."""
    return False


# ==========================================
# 2. CONTROLE VISUAL (ABRIR/FECHAR MODAL)
# ==========================================
@app.callback(
    Output("modal-novo-lancamento", "is_open", allow_duplicate=True),
    Output("store-transacao-id-editar", "data", allow_duplicate=True),
    Input("btn-novo-lancamento", "n_clicks"),
    Input("btn-cancelar-modal", "n_clicks"),
    State("modal-novo-lancamento", "is_open"),
    prevent_initial_call=True,
)
def toggle_modal(n_novo, n_cancelar, is_open):
    """Abre o modal no botão global e fecha no cancelar."""
    trigger_id = ctx.triggered_id

    if trigger_id == "btn-novo-lancamento" and n_novo:
        return True, None

    if trigger_id == "btn-cancelar-modal" and n_cancelar:
        return False, None

    return no_update, no_update


@app.callback(
    Output("data-pagamento", "disabled"),
    Input("switch-pago", "value"),
    prevent_initial_call=True,
)
def toggle_data_pagamento(pago):
    """Habilita a data de pagamento apenas quando o lançamento já foi pago."""
    return not pago


# ==========================================
# 3. FORMULÁRIO DINÂMICO (RECEITA/DESPESA X TRANSFERÊNCIA)
# ==========================================
@app.callback(
    Output("standard-section", "style"),
    Output("transfer-section", "style"),
    Input("tipo-lancamento", "value"),
    prevent_initial_call=True,
)
def alternar_secoes_transacao(tipo):
    """Alterna entre os campos padrão e os campos de transferência."""
    if tipo == "TRANSFER":
        return {"display": "none"}, {"display": "block"}
    return {"display": "block"}, {"display": "none"}


# ==========================================
# 4. CARREGAR OPÇÕES (CATEGORIAS E CONTAS)
# ==========================================
@app.callback(
    Output("select-categoria", "options"),
    Output("select-conta", "options"),
    Output("select-conta-destino", "options"),
    Input("tipo-lancamento", "value"),
    Input("auth-store", "data"),
    Input("modal-novo-lancamento", "is_open"),
    prevent_initial_call=True,
)
def carregar_opcoes(tipo, auth_data, is_open):
    """Carrega categorias e contas do usuário logado."""
    if not is_open or not auth_data:
        return no_update, no_update, no_update

    try:
        user_id = resolve_user(auth_data)
        with get_db_session() as db:
            category_service = CategoryService(db)
            categories = category_service.get_available_categories(user_id, TransactionType(tipo))
            category_options = [
                {"label": f"{category.icon} {category.name}", "value": category.id}
                for category in categories
            ]

            account_service = AccountService(db)
            accounts = account_service.get_user_accounts(user_id)
            account_options = [{"label": account.name, "value": account.id} for account in accounts]

            return category_options, account_options, account_options
    except AuthenticationError:
        return [], [], []
    except Exception as exc:
        app_logger.error(f"Erro ao carregar opções do modal: {exc}")
        return [], [], []


# ==========================================
# 5. PREENCHER FORMULÁRIO (CRIAR OU EDITAR)
# ==========================================
@app.callback(
    Output("input-valor", "value"),
    Output("input-descricao", "value"),
    Output("select-categoria", "value"),
    Output("select-conta", "value"),
    Output("select-conta-destino", "value"),
    Output("tipo-lancamento", "value"),
    Output("data-compra", "date"),
    Output("data-vencimento", "date"),
    Output("data-pagamento", "date"),
    Output("switch-pago", "value"),
    Output("check-recorrencia", "value"),
    Output("input-parcela-atual", "value"),
    Output("input-total-parcelas", "value"),
    Output("modal-header-title", "children"),
    Input("modal-novo-lancamento", "is_open"),
    State("store-transacao-id-editar", "data"),
    State("auth-store", "data"),
    prevent_initial_call=True,
)
def preencher_formulario(is_open, edit_id, auth_data):
    """Preenche o modal para criação ou edição."""
    if not is_open:
        return (no_update,) * 14

    hoje = date.today()

    if not edit_id:
        return (
            "",
            "",
            None,
            None,
            None,
            "EXPENSE",
            hoje,
            hoje,
            hoje,
            True,
            [],
            1,
            1,
            "Novo Lançamento",
        )

    try:
        user_id = resolve_user(auth_data)
        with get_db_session() as db:
            transaction = (
                db.query(Transaction)
                .filter(
                    Transaction.id == edit_id,
                    Transaction.user_id == user_id,
                )
                .first()
            )

            if not transaction:
                return (no_update,) * 14

            tipo = transaction.transaction_type.value
            pago = transaction.paid_date is not None
            valor = (
                f"{transaction.base_amount:,.2f}".replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
            recorrencia = ["recorrente"] if transaction.is_recurring else []

            return (
                valor,
                transaction.description,
                transaction.category_id,
                transaction.account_id,
                transaction.destination_account_id,
                tipo,
                transaction.purchase_date,
                transaction.due_date,
                transaction.paid_date,
                pago,
                recorrencia,
                transaction.installment_number,
                transaction.total_installments,
                "Editar Lançamento",
            )
    except AuthenticationError:
        return (no_update,) * 14
    except Exception as exc:
        app_logger.error(f"Erro ao carregar lançamento para edição: {exc}")
        return (no_update,) * 14


# ==========================================
# 6. SALVAR (RECEITA, DESPESA OU TRANSFERÊNCIA)
# ==========================================
@app.callback(
    Output("feedback-transacao", "children"),
    Output("store-reload-dashboard", "data"),
    Output("modal-novo-lancamento", "is_open", allow_duplicate=True),
    Input("btn-salvar-lancamento", "n_clicks"),
    State("auth-store", "data"),
    State("store-transacao-id-editar", "data"),
    State("tipo-lancamento", "value"),
    State("input-valor", "value"),
    State("input-descricao", "value"),
    State("select-categoria", "value"),
    State("select-conta", "value"),
    State("select-conta-destino", "value"),
    State("data-compra", "date"),
    State("data-vencimento", "date"),
    State("data-pagamento", "date"),
    State("switch-pago", "value"),
    State("check-recorrencia", "value"),
    State("input-parcela-atual", "value"),
    State("input-total-parcelas", "value"),
    State("store-reload-dashboard", "data"),
    prevent_initial_call=True,
)
def salvar_transacao(
    n_clicks,
    auth_data,
    edit_id,
    tipo,
    valor,
    descricao,
    categoria_id,
    conta_id,
    conta_destino_id,
    data_compra,
    data_vencimento,
    data_pagamento,
    pago,
    recorrencia,
    parcela_atual,
    total_parcelas,
    reload_counter,
):
    """Cria ou atualiza a transação selecionada."""
    if not n_clicks:
        return no_update, no_update, no_update

    try:
        user_id = resolve_user(auth_data)

        if not valor:
            raise ValueError("Valor é obrigatório")
        if not data_compra or not data_vencimento:
            raise ValueError("Datas de compra e vencimento são obrigatórias")

        valor_texto = str(valor).replace("R$", "").replace(" ", "").strip()
        if "," in valor_texto:
            valor_limpo = valor_texto.replace(".", "").replace(",", ".")
        else:
            valor_limpo = valor_texto

        try:
            valor_decimal = Decimal(valor_limpo)
        except InvalidOperation:
            raise ValueError("Valor inválido")

        if valor_decimal <= 0:
            raise ValueError("Valor deve ser maior que zero")

        data_purchase = date.fromisoformat(data_compra)
        data_due = date.fromisoformat(data_vencimento)
        if data_due < data_purchase:
            raise ValueError("Vencimento não pode ser anterior à data de compra")

        data_paid = None
        if pago:
            data_paid = date.fromisoformat(data_pagamento) if data_pagamento else data_due

        if tipo == "TRANSFER":
            if edit_id:
                raise ValueError("Edição de transferência ainda não suportada")
            if not conta_id or not conta_destino_id:
                raise ValueError("Selecione as contas de origem e destino")
            if int(conta_id) == int(conta_destino_id):
                raise ValueError("Conta de origem e destino devem ser diferentes")

            with get_db_session() as db:
                balance = BalanceService(db).get_account_balance(int(conta_id), user_id)
                if pago and valor_decimal > balance:
                    raise ValueError(
                        "Saldo insuficiente na conta de origem para esta transferência"
                    )

                categorias = CategoryService(db).get_available_categories(
                    user_id, TransactionType.TRANSFER
                )
                if not categorias:
                    raise ValueError("Categoria de transferência não encontrada")
                categoria_transferencia = categorias[0].id

                TransferService(db).transfer(
                    user_id=user_id,
                    from_account_id=int(conta_id),
                    to_account_id=int(conta_destino_id),
                    amount=valor_decimal,
                    due_date=data_due,
                    paid_date=data_paid,
                    description=descricao.strip() if descricao else "Transferência entre contas",
                    category_id=categoria_transferencia,
                )

            return (
                dbc.Alert(
                    "✅ Transferência criada com sucesso!",
                    color="success",
                    duration=3000,
                ),
                (reload_counter or 0) + 1,
                False,
            )

        if not categoria_id:
            raise ValueError("Selecione uma categoria")
        if not conta_id:
            raise ValueError("Selecione uma conta")

        is_recorrente = "recorrente" in (recorrencia or [])

        payload = TransactionCreate(
            description=descricao.strip() if descricao else "Sem descrição",
            base_amount=valor_decimal,
            transaction_type=TransactionType(tipo),
            category_id=int(categoria_id),
            account_id=int(conta_id),
            purchase_date=data_purchase,
            due_date=data_due,
            paid_date=data_paid,
            is_recurring=is_recorrente,
            installment_number=int(parcela_atual or 1),
            total_installments=int(total_parcelas or 1),
            notes="",
        )

        with get_db_session() as db:
            finance_service = FinanceService(db)
            if edit_id:
                finance_service.update_transaction(
                    edit_id,
                    user_id,
                    TransactionUpdate(**payload.model_dump()),
                )
                mensagem = "✅ Lançamento atualizado com sucesso!"
            else:
                finance_service.create_transaction(user_id, payload)
                mensagem = "✅ Lançamento criado com sucesso!"

        return (
            dbc.Alert(mensagem, color="success", duration=3000),
            (reload_counter or 0) + 1,
            False,
        )

    except AuthenticationError as exc:
        return (
            dbc.Alert(f"⚠️ {exc.message}", color="warning", duration=4000),
            no_update,
            True,
        )
    except (ValueError, TransferError) as exc:
        return (
            dbc.Alert(f"⚠️ {str(exc)}", color="warning", duration=4000),
            no_update,
            True,
        )
    except Exception as exc:
        app_logger.error(f"Erro ao salvar transação: {exc}")
        return (
            dbc.Alert(
                "❌ Erro inesperado ao salvar. Tente novamente.",
                color="danger",
                duration=5000,
            ),
            no_update,
            True,
        )
