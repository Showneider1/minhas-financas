"""
Callbacks de extrato com paginação e filtros otimizados.
"""
from dash import Input, Output, State, html, no_update
import dash_bootstrap_components as dbc
from datetime import datetime, date
from app import app
from database.connection import get_db_session
from services.finance_service import FinanceService
from schemas.transaction_schema import TransactionFilter
from database.models.category import TransactionType
from database.models.transaction import TransactionStatus
from config.logging_config import app_logger
from sqlalchemy import func



@app.callback(
    Output("tabela-extrato", "children"),
    Output("total-entradas-extrato", "children"),
    Output("total-saidas-extrato", "children"),
    Output("saldo-periodo-extrato", "children"),
    Input("store-user-id", "data"),
    Input("store-reload-dashboard", "data"),
    Input("busca-extrato", "value"),
    Input("extrato-periodo", "start_date"),
    Input("extrato-periodo", "end_date"),
    Input("extrato-tipo", "value"),
    Input("extrato-status", "value"),
)
def atualizar_extrato(
    user_id,
    reload_trigger,
    busca,
    start_date,
    end_date,
    tipos,
    status_list,
):
    """
    Atualiza extrato conforme filtros aplicados.
    """
    print(f"\n📋 ATUALIZANDO EXTRATO")
    print(f"   user_id: {user_id}")
    print(f"   reload_trigger: {reload_trigger}")
    
    try:
        if not user_id:
            return [], "R$ 0,00", "R$ 0,00", "R$ 0,00"
        
        # Converte datas
        if start_date:
            data_inicio = datetime.fromisoformat(start_date).date()
        else:
            data_inicio = date.today().replace(day=1)
        
        if end_date:
            data_fim = datetime.fromisoformat(end_date).date()
        else:
            data_fim = date.today()
        
        print(f"   📅 Período: {data_inicio} até {data_fim}")
        
        with get_db_session() as db:
            from database.models.transaction import Transaction
            from database.models.category import Category
            
            # Query base - MODIFICADO: remove filtro paid_date.isnot(None)
            query = db.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.due_date >= data_inicio,
                Transaction.due_date <= data_fim
            )
            
            # Aplica filtros
            if busca:
                query = query.filter(Transaction.description.ilike(f"%{busca}%"))
            
            if tipos:
                query = query.filter(Transaction.transaction_type.in_(tipos))
            
            # Filtro de status - CORRIGIDO
            if status_list:
                print(f"   🔍 Filtrando por status: {status_list}")
                if "PAID" in status_list and "PENDING" not in status_list:
                    # Apenas pagos
                    query = query.filter(Transaction.paid_date.isnot(None))
                elif "PENDING" in status_list and "PAID" not in status_list:
                    # Apenas pendentes
                    query = query.filter(Transaction.paid_date.is_(None))
                # Se ambos ou nenhum, não filtra
            
            # Ordena
            query = query.order_by(Transaction.due_date.desc())
            
            # Executa
            transactions = query.all()
            
            print(f"   📊 Total de transações: {len(transactions)}")
            
            # Calcula totais - apenas transações pagas
            entradas = sum(
                t.base_amount for t in transactions 
                if t.transaction_type == TransactionType.INCOME and t.paid_date is not None
            )
            saidas = sum(
                t.base_amount for t in transactions 
                if t.transaction_type == TransactionType.EXPENSE and t.paid_date is not None
            )
            saldo = entradas - saidas
            
            print(f"   💵 Entradas: {entradas}")
            print(f"   💸 Saídas: {saidas}")
            print(f"   💰 Saldo: {saldo}")
            
            # Gera cards de transações
            cards = []
            for transaction in transactions:
                card = gerar_card_transacao(transaction)
                cards.append(card)
            
            if not cards:
                cards = [
                    dbc.Alert(
                        "Nenhuma transação encontrada para os filtros aplicados.",
                        color="info",
                        className="text-center",
                    )
                ]
            
            # Formata valores
            entradas_str = f"R$ {entradas:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            saidas_str = f"R$ {saidas:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            saldo_str = f"R$ {saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            return cards, entradas_str, saidas_str, saldo_str
    
    except Exception as e:
        app_logger.error(f"Erro ao atualizar extrato: {e}")
        import traceback
        traceback.print_exc()
        return [dbc.Alert(f"Erro: {str(e)}", color="danger")], "R$ 0,00", "R$ 0,00", "R$ 0,00"

def gerar_card_transacao(transaction):
    """
    Gera card visual para uma transação.
    """
    # Define cor e ícone baseado no tipo
    if transaction.transaction_type == TransactionType.INCOME:
        cor = "success"
        icone = "bi-arrow-up-circle"
        sinal = "+"
    else:
        cor = "danger"
        icone = "bi-arrow-down-circle"
        sinal = "-"
    
    # Badge de status
    status_badges = {
        TransactionStatus.PAID: ("success", "Pago"),
        TransactionStatus.PENDING: ("warning", "Pendente"),
        TransactionStatus.CANCELLED: ("secondary", "Cancelado"),  # ← Corrigido
    }
    badge_color, badge_text = status_badges.get(transaction.status, ("secondary", "N/A"))
    
    # Formata valor
    valor_str = f"R$ {transaction.base_amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    # Formata data
    data_str = transaction.paid_date.strftime("%d/%m/%Y") if transaction.paid_date else "Sem data"
    
    card = dbc.Card(
        dbc.CardBody(
            dbc.Row(
                [
                    # Ícone
                    dbc.Col(
                        html.I(className=f"{icone} fs-3 text-{cor}"),
                        width="auto",
                        className="d-flex align-items-center",
                    ),
                    # Informações
                    dbc.Col(
                        [
                            html.H6(
                                transaction.description or "Sem descrição",
                                className="mb-1 fw-bold",
                            ),
                            html.Small(
                                [
                                    html.Span(
                                        f"{transaction.category.icon or '📁'} {transaction.category.name}",
                                        className="me-3",
                                    ),
                                    html.Span(
                                        f"📅 {data_str}",
                                    ),
                                ],
                                className="text-muted",
                            ),
                        ],
                        className="d-flex flex-column justify-content-center",
                    ),
                    # Status
                    dbc.Col(
                        dbc.Badge(
                            badge_text,
                            color=badge_color,
                            className="px-3 py-2",
                        ),
                        width="auto",
                        className="d-flex align-items-center",
                    ),
                    # Valor
                    dbc.Col(
                        html.H5(
                            f"{sinal} {valor_str}",
                            className=f"mb-0 text-{cor} fw-bold text-end",
                        ),
                        width=2,
                        className="d-flex align-items-center justify-content-end",
                    ),
                ],
                className="align-items-center",
            )
        ),
        className="mb-2 shadow-sm border-0 hover-shadow",
        style={"cursor": "pointer"},
    )
    
    return card




@app.callback(
    Output("collapse-filtros-extrato", "is_open"),
    Input("btn-toggle-filtros", "n_clicks"),
    State("collapse-filtros-extrato", "is_open"),
    prevent_initial_call=True,
)
def toggle_filtros(n, is_open):
    """
    Abre/fecha filtros avançados.
    """
    if n:
        return not is_open
    return is_open
