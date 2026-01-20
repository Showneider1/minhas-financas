from dash import Input, Output, State, callback_context, no_update
from dash import html
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
import pandas as pd

from app import app
from database.connection import get_db_session
from services.budget_service import BudgetService
from services.category_service import CategoryService
from database.models.category import TransactionType, Category
from database.models.transaction import Transaction, TransactionStatus
from sqlalchemy import func, extract

# ==========================================
# 1. ORQUESTRADOR DO DASHBOARD (ATUALIZA TUDO)
# ==========================================
@app.callback(
    Output("kpi-saldo", "children"),
    Output("kpi-receita", "children"),
    Output("kpi-despesa", "children"),
    Output("grafico-fluxo-caixa", "figure"),
    Output("grafico-categorias", "figure"),
    Output("container-budgets", "children"), # Barra de progresso das metas
    
    Input("dashboard-periodo", "start_date"),
    Input("dashboard-periodo", "end_date"),
    Input("store-reload-dashboard", "data"),
    State("store-user-id", "data"),
)
def atualizar_dashboard(start_date, end_date, reload, user_id):
    if not user_id: 
        return "R$ 0,00", "R$ 0,00", "R$ 0,00", go.Figure(), go.Figure(), []

    # 1. Tratamento de Datas
    if not start_date: start_date = date.today().replace(day=1).isoformat()
    if not end_date: end_date = date.today().isoformat()
    
    d_inicio = date.fromisoformat(start_date)
    d_fim = date.fromisoformat(end_date)

    with get_db_session() as db:
        # ==========================================
        # BUSCA DADOS (Query Otimizada em DataFrame)
        # ==========================================
        # Trazemos tudo de uma vez para não ficar indo no banco 5 vezes
        query = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.paid_date >= d_inicio,
            Transaction.paid_date <= d_fim,
            Transaction.status == TransactionStatus.PAID # Só considera o que foi PAGO
        )
        df = pd.read_sql(query.statement, db.bind)

        # ==========================
        # A. KPIs (Saldo, Receita, Despesa)
        # ==========================
        val_receita = df[df["transaction_type"] == TransactionType.INCOME.value]["base_amount"].sum() if not df.empty else 0.0
        val_despesa = df[df["transaction_type"] == TransactionType.EXPENSE.value]["base_amount"].sum() if not df.empty else 0.0
        val_saldo = val_receita - val_despesa

        kpi_saldo = f"R$ {val_saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        kpi_receita = f"R$ {val_receita:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        kpi_despesa = f"R$ {val_despesa:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        # ==========================
        # B. GRÁFICO FLUXO (Diário)
        # ==========================
        if not df.empty:
            df_fluxo = df.groupby("paid_date")[["base_amount"]].sum().reset_index()
            fig_fluxo = px.bar(df_fluxo, x="paid_date", y="base_amount", title="Movimentação Diária")
            fig_fluxo.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=300, template="plotly_white")
        else:
            fig_fluxo = go.Figure().add_annotation(text="Sem dados no período", showarrow=False)

        # ==========================
        # C. GRÁFICO CATEGORIAS (Despesas)
        # ==========================
        if not df.empty:
            # Filtra só despesas
            df_desp = df[df["transaction_type"] == TransactionType.EXPENSE.value]
            
            if not df_desp.empty:
                # Agrupa por Categoria ID
                df_cat_group = df_desp.groupby("category_id")["base_amount"].sum().reset_index()
                
                # Busca nomes das categorias no banco
                cat_ids = df_cat_group["category_id"].unique().tolist()
                cats_db = db.query(Category).filter(Category.id.in_(cat_ids)).all()
                cat_map = {c.id: c.name for c in cats_db}
                
                df_cat_group["nome"] = df_cat_group["category_id"].map(cat_map)
                
                fig_pizza = px.pie(df_cat_group, values="base_amount", names="nome", hole=0.4)
                fig_pizza.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=300, template="plotly_white")
            else:
                fig_pizza = go.Figure().add_annotation(text="Sem despesas", showarrow=False)
        else:
            fig_pizza = go.Figure().add_annotation(text="Sem dados", showarrow=False)

        # ==========================
        # D. PROGRESSO DAS METAS (Budgets)
        # ==========================
        # Usamos o mês da data de INÍCIO do filtro para saber qual meta carregar
        mes_ref = d_inicio.month
        ano_ref = d_inicio.year
        
        budget_service = BudgetService(db)
        budgets = budget_service.get_budgets_by_period(user_id, mes_ref, ano_ref)
        
        progress_bars = []
        if not budgets:
            progress_bars.append(html.P(f"Nenhuma meta definida para {mes_ref}/{ano_ref}.", className="text-muted small"))
        else:
            for budget in budgets:
                # Quanto gastou nesta categoria neste mês? (Query direta para precisão)
                gasto_real = db.query(func.sum(Transaction.base_amount)).filter(
                    Transaction.user_id == user_id,
                    Transaction.category_id == budget.category_id,
                    Transaction.transaction_type == TransactionType.EXPENSE,
                    Transaction.status == TransactionStatus.PAID,
                    extract('month', Transaction.paid_date) == mes_ref,
                    extract('year', Transaction.paid_date) == ano_ref
                ).scalar() or 0.0
                
                pct = (gasto_real / budget.amount) * 100 if budget.amount > 0 else 0
                
                # Cores dinâmicas
                if pct < 80: cor = "success"     # Verde (Tranquilo)
                elif pct < 100: cor = "warning"  # Amarelo (Atenção)
                else: cor = "danger"             # Vermelho (Estourou)
                
                # Nome da categoria (busca do objeto ou query)
                nome_cat = budget.category.name if budget.category else "Categoria"
                icon_cat = budget.category.icon if budget.category and budget.category.icon else ""

                progress_bars.append(html.Div([
                    html.Div([
                        html.Span(f"{icon_cat} {nome_cat}", className="fw-bold"),
                        html.Span(f"R$ {gasto_real:,.0f} / {budget.amount:,.0f}", className="float-end small")
                    ]),
                    dbc.Progress(value=pct, color=cor, className="mb-2", style={"height": "10px"}),
                ]))

        return kpi_saldo, kpi_receita, kpi_despesa, fig_fluxo, fig_pizza, progress_bars

# ==========================================
# 2. MODAL DE METAS (ABRIR/FECHAR)
# ==========================================
@app.callback(
    Output("modal-budget", "is_open"),
    Output("select-budget-category", "options"),
    Input("btn-open-budget", "n_clicks"),
    Input("btn-close-budget", "n_clicks"),
    State("modal-budget", "is_open"),
    State("store-user-id", "data"),
    prevent_initial_call=True
)
def toggle_budget_modal(n_open, n_close, is_open, user_id):
    ctx = callback_context
    if not ctx.triggered: return no_update
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]

    # Abrir: Carrega categorias
    if trigger_id == "btn-open-budget":
        if not user_id: return no_update, []
        try:
            with get_db_session() as db:
                cat_service = CategoryService(db)
                cats = cat_service.get_available_categories(user_id, TransactionType.EXPENSE)
                options = [{"label": f"{c.icon or ''} {c.name}", "value": c.id} for c in cats]
            return True, options
        except Exception:
            return True, []

    # Fechar
    return False, no_update

# ==========================================
# 3. SALVAR META
# ==========================================
@app.callback(
    Output("budget-feedback", "children"),
    Output("store-reload-dashboard", "data", allow_duplicate=True),
    Input("btn-save-budget", "n_clicks"),
    State("select-budget-category", "value"),
    State("input-budget-amount", "value"),
    State("dashboard-periodo", "start_date"), # Data referência para o mês da meta
    State("store-user-id", "data"),
    prevent_initial_call=True
)
def salvar_meta(n_clicks, category_id, amount, start_date, user_id):
    if not n_clicks: return no_update
    
    if not category_id or not amount:
        return dbc.Alert("Preencha categoria e valor!", color="warning"), no_update

    try:
        # Define Mês/Ano com base no filtro do Dashboard
        if start_date:
            data_ref = date.fromisoformat(start_date)
        else:
            data_ref = date.today()
            
        mes = data_ref.month
        ano = data_ref.year

        with get_db_session() as db:
            service = BudgetService(db)
            service.save_budget(
                user_id=user_id,
                category_id=int(category_id),
                amount=float(amount),
                month=mes,
                year=ano
            )
            
        return dbc.Alert(f"✅ Meta salva para {mes}/{ano}!", color="success", duration=4000), True

    except Exception as e:
        return dbc.Alert(f"Erro: {str(e)}", color="danger"), no_update