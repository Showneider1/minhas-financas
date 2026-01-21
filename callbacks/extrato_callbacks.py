"""
Callbacks da página de extrato.
"""
from dash import Input, Output, State, html, callback_context, no_update
import dash_bootstrap_components as dbc
from datetime import datetime, date
from app import app
from database.connection import get_db_session
from database.repositories.transaction_repo import TransactionRepository
from services.account_service import AccountService
from services.category_service import CategoryService
from config.logging_config import app_logger

# ========================================================
# 1. CARREGAR OPÇÕES DOS FILTROS (Contas e Categorias)
# ========================================================
@app.callback(
    Output("extrato-filter-account", "options"),
    Output("extrato-filter-category", "options"),
    Input("url", "pathname"), # Dispara ao entrar na página
    State("store-user-id", "data"),
)
def load_filters_options(pathname, user_id):
    if not user_id or pathname != "/extrato":
        return no_update, no_update
    
    try:
        with get_db_session() as db:
            # Contas
            accounts = AccountService(db).get_user_accounts(user_id)
            acc_opts = [{"label": "Todas as contas", "value": ""}]
            acc_opts.extend([{"label": acc.name, "value": acc.id} for acc in accounts])
            
            # Categorias
            cats = CategoryService(db).get_user_categories(user_id)
            cat_opts = [{"label": "Todas", "value": ""}]
            cat_opts.extend([{"label": f"{c.icon or ''} {c.name}", "value": c.id} for c in cats])
            
            return acc_opts, cat_opts
    except Exception as e:
        app_logger.error(f"Erro ao carregar filtros: {e}")
        return [], []

# ========================================================
# 2. ATUALIZAR TABELA E CARDS DE RESUMO
# ========================================================
@app.callback(
    Output("extrato-table-container", "children"),
    Output("extrato-summary-cards", "children"),
    
    # Triggers (Filtros)
    Input("extrato-filter-date", "start_date"),
    Input("extrato-filter-date", "end_date"),
    Input("extrato-filter-account", "value"),
    Input("extrato-filter-category", "value"),
    Input("extrato-filter-type", "value"),
    Input("extrato-filter-status", "value"),
    Input("extrato-reload-trigger", "data"), # Caso adicione/edite algo
    
    State("store-user-id", "data"),
)
def update_extrato(start_date, end_date, acc_id, cat_id, type_, status, _, user_id):
    if not user_id:
        return html.Div("Usuário não identificado"), []

    try:
        # Tratamento de Datas
        dt_start = datetime.fromisoformat(start_date).date() if start_date else None
        dt_end = datetime.fromisoformat(end_date).date() if end_date else None
        
        # Tratamento de Valores Vazios dos Selects
        acc_id = int(acc_id) if acc_id else None
        cat_id = int(cat_id) if cat_id else None
        type_filter = type_ if type_ != "ALL" else None
        status_filter = status if status != "ALL" else None

        with get_db_session() as db:
            repo = TransactionRepository(db)
            transactions = repo.get_filtered(
                user_id=user_id,
                start_date=dt_start,
                end_date=dt_end,
                account_id=acc_id,
                category_id=cat_id,
                type_=type_filter,
                status=status_filter
            )

            if not transactions:
                return (
                    html.Div([
                        html.I(className="bi bi-search display-4 text-muted mb-3"),
                        html.H5("Nenhum lançamento encontrado", className="text-muted"),
                        html.P("Tente ajustar os filtros.", className="text-muted")
                    ], className="text-center py-5"), 
                    []
                )

            # --- CONSTRUÇÃO DA TABELA ---
            rows = []
            total_receitas = 0
            total_despesas = 0

            for t in transactions:
                # Cálculos para os cards
                if t.transaction_type.value == "INCOME":
                    total_receitas += t.base_amount
                elif t.transaction_type.value == "EXPENSE":
                    total_despesas += t.base_amount

                # Formatação Visual
                is_income = t.transaction_type.value == "INCOME"
                color_class = "text-success" if is_income else "text-danger"
                signal = "+" if is_income else "-"
                
                # Ícone da Categoria
                cat_icon = t.category.icon if t.category else "📝"
                cat_name = t.category.name if t.category else "Sem categoria"
                
                # Status Badge
                is_paid = t.paid_date is not None
                status_badge = dbc.Badge(
                    "Pago" if is_paid else "Pendente",
                    color="success" if is_paid else "warning",
                    className="rounded-pill"
                )
                
                # Data (Vencimento vs Pagamento)
                data_show = t.paid_date if is_paid else t.due_date
                data_str = data_show.strftime("%d/%m/%Y")
                
                # Linha da Tabela
                rows.append(html.Tr([
                    html.Td(html.Div([
                        html.Div(data_str, className="fw-bold"),
                        html.Small("Data Pgto." if is_paid else "Vencimento", className="text-muted")
                    ])),
                    html.Td(html.Div([
                        html.Div(t.description, className="fw-bold"),
                        html.Small(f"{cat_icon} {cat_name}", className="text-muted")
                    ])),
                    html.Td(t.account.name if t.account else "-"),
                    html.Td(status_badge, className="text-center"),
                    html.Td(
                        f"{signal} R$ {t.base_amount:,.2f}", 
                        className=f"text-end fw-bold {color_class}"
                    ),
                    # Botões de Ação (Placeholder)
                    html.Td(
                        html.Div([
                            dbc.Button(html.I(className="bi bi-pencil"), size="sm", color="light", className="me-1"),
                            dbc.Button(html.I(className="bi bi-trash"), size="sm", color="light", className="text-danger"),
                        ], className="d-flex justify-content-end")
                    )
                ]))

            table = dbc.Table(
                [
                    html.Thead(html.Tr([
                        html.Th("Data"),
                        html.Th("Descrição"),
                        html.Th("Conta"),
                        html.Th("Status", className="text-center"),
                        html.Th("Valor", className="text-end"),
                        html.Th("Ações", className="text-end"),
                    ])),
                    html.Tbody(rows)
                ],
                hover=True,
                responsive=True,
                striped=True,
                className="align-middle"
            )

            # --- CONSTRUÇÃO DOS CARDS DE RESUMO ---
            cards = [
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.H6("Receitas (Filtro)", className="text-muted mb-1"),
                    html.H4(f"R$ {total_receitas:,.2f}", className="text-success fw-bold")
                ]), className="shadow-sm border-0 border-start border-success border-5"), width=12, md=4),
                
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.H6("Despesas (Filtro)", className="text-muted mb-1"),
                    html.H4(f"R$ {total_despesas:,.2f}", className="text-danger fw-bold")
                ]), className="shadow-sm border-0 border-start border-danger border-5"), width=12, md=4),
                
                dbc.Col(dbc.Card(dbc.CardBody([
                    html.H6("Resultado", className="text-muted mb-1"),
                    html.H4(f"R$ {total_receitas - total_despesas:,.2f}", className="text-primary fw-bold")
                ]), className="shadow-sm border-0 border-start border-primary border-5"), width=12, md=4),
            ]

            return table, cards

    except Exception as e:
        app_logger.error(f"Erro ao atualizar extrato: {e}")
        import traceback
        traceback.print_exc()
        return html.Div(f"Erro: {str(e)}", className="text-danger"), []