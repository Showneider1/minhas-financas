"""
Callbacks da página de dashboard.
"""
from dash import Input, Output, State, no_update
from dash import html
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime, timedelta
from app import app
from database.connection import get_db_session
from database.models.transaction import Transaction
from sqlalchemy import func
import logging


logger = logging.getLogger(__name__)


# ==========================================
# DEBUG USER ID
# ==========================================


@app.callback(
    Output("kpi-saldo", "className"),
    Input("store-user-id", "data"),
)
def debug_user_id(user_id):
    """Debug: verifica se user_id está chegando."""
    print(f"\n🐛 DEBUG USER ID: {user_id}")
    return "fw-bold mb-1"


# ==========================================
# KPI SALDO
# ==========================================


@app.callback(
    Output("kpi-saldo", "children"),
    Output("kpi-saldo-variacao", "children"),
    Input("dashboard-periodo", "start_date"),
    Input("dashboard-periodo", "end_date"),
    Input("store-reload-dashboard", "data"),
    State("store-user-id", "data"),
)
def atualizar_saldo(start_date, end_date, reload_trigger, user_id):
    """Atualiza KPI de saldo total."""
    print(f"\n🔄 ATUALIZANDO SALDO")
    print(f"   user_id: {user_id}")
    print(f"   reload_trigger: {reload_trigger}")
    
    if not user_id:
        print(f"   ❌ Sem user_id")
        return "R$ 0,00", ""
    
    try:
        with get_db_session() as db:
            # Saldo = Receitas - Despesas
            receitas = db.query(
                func.sum(Transaction.base_amount)
            ).filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == "INCOME",
                Transaction.paid_date.isnot(None)
            ).scalar() or 0
            
            despesas = db.query(
                func.sum(Transaction.base_amount)
            ).filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == "EXPENSE",
                Transaction.paid_date.isnot(None)
            ).scalar() or 0
            
            saldo_atual = receitas - despesas
            
            print(f"   📊 Receitas: {receitas}")
            print(f"   📊 Despesas: {despesas}")
            print(f"   💰 Saldo calculado: {saldo_atual}")
            
            # Formata valores
            saldo_str = f"R$ {saldo_atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            print(f"   ✅ Saldo formatado: {saldo_str}")
            
            return saldo_str, ""
    
    except Exception as e:
        logger.error(f"Erro ao atualizar saldo: {e}")
        import traceback
        traceback.print_exc()
        return "R$ 0,00", ""



# ==========================================
# KPI RECEITAS
# ==========================================


@app.callback(
    Output("kpi-receita", "children"),
    Output("kpi-receita-variacao", "children"),
    Input("dashboard-periodo", "start_date"),
    Input("dashboard-periodo", "end_date"),
    Input("store-reload-dashboard", "data"),
    State("store-user-id", "data"),
)
def atualizar_receitas(start_date, end_date, reload_trigger, user_id):
    """Atualiza KPI de receitas."""
    print(f"\n🔄 ATUALIZANDO RECEITAS")
    print(f"   user_id: {user_id}")
    print(f"   reload_trigger: {reload_trigger}")
    
    if not user_id:
        return "R$ 0,00", ""
    
    try:
        # Converte datas
        if start_date:
            data_inicio = datetime.fromisoformat(start_date)
        else:
            data_inicio = datetime.now().replace(day=1)
        
        if end_date:
            data_fim = datetime.fromisoformat(end_date)
        else:
            data_fim = datetime.now()
        
        print(f"   📅 Período: {data_inicio} até {data_fim}")
        
        with get_db_session() as db:
            # Receitas do período
            result = db.query(
                func.sum(Transaction.base_amount)
            ).filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == "INCOME",
                Transaction.paid_date.isnot(None),
                Transaction.paid_date >= data_inicio,
                Transaction.paid_date <= data_fim
            ).scalar()
            
            receita_atual = result or 0
            
            print(f"   💵 Receita calculada: {receita_atual}")
            
            # Formata valores
            receita_str = f"R$ {receita_atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            return receita_str, ""
    
    except Exception as e:
        logger.error(f"Erro ao atualizar receitas: {e}")
        import traceback
        traceback.print_exc()
        return "R$ 0,00", ""


# ==========================================
# KPI DESPESAS
# ==========================================


@app.callback(
    Output("kpi-despesa", "children"),
    Output("kpi-despesa-variacao", "children"),
    Input("dashboard-periodo", "start_date"),
    Input("dashboard-periodo", "end_date"),
    Input("store-reload-dashboard", "data"),
    State("store-user-id", "data"),
)
def atualizar_despesas(start_date, end_date, reload_trigger, user_id):
    """Atualiza KPI de despesas."""
    print(f"\n🔄 ATUALIZANDO DESPESAS")
    print(f"   user_id: {user_id}")
    print(f"   reload_trigger: {reload_trigger}")
    
    if not user_id:
        return "R$ 0,00", ""
    
    try:
        # Converte datas
        if start_date:
            data_inicio = datetime.fromisoformat(start_date)
        else:
            data_inicio = datetime.now().replace(day=1)
        
        if end_date:
            data_fim = datetime.fromisoformat(end_date)
        else:
            data_fim = datetime.now()
        
        print(f"   📅 Período: {data_inicio} até {data_fim}")
        
        with get_db_session() as db:
            # Despesas do período
            result = db.query(
                func.sum(Transaction.base_amount)
            ).filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == "EXPENSE",
                Transaction.paid_date.isnot(None),
                Transaction.paid_date >= data_inicio,
                Transaction.paid_date <= data_fim
            ).scalar()
            
            despesa_atual = result or 0
            
            print(f"   💸 Despesa calculada: {despesa_atual}")
            
            # Formata valores
            despesa_str = f"R$ {despesa_atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            return despesa_str, ""
    
    except Exception as e:
        logger.error(f"Erro ao atualizar despesas: {e}")
        import traceback
        traceback.print_exc()
        return "R$ 0,00", ""


# ==========================================
# GRÁFICO FLUXO DE CAIXA
# ==========================================


@app.callback(
    Output("grafico-fluxo-caixa", "figure"),
    Input("dashboard-periodo", "start_date"),
    Input("dashboard-periodo", "end_date"),
    Input("store-reload-dashboard", "data"),
    State("store-user-id", "data"),
)
def atualizar_grafico_fluxo(start_date, end_date, reload_trigger, user_id):
    """Atualiza gráfico de fluxo de caixa."""
    if not user_id:
        return go.Figure()
    
    try:
        # Converte datas
        if start_date:
            data_inicio = datetime.fromisoformat(start_date)
        else:
            data_inicio = datetime.now().replace(day=1)
        
        with get_db_session() as db:
            # Query para receitas e despesas por dia
            transactions = db.query(
                func.date(Transaction.paid_date).label("periodo"),
                Transaction.transaction_type,
                func.sum(Transaction.base_amount).label("total")
            ).filter(
                Transaction.user_id == user_id,
                Transaction.paid_date.isnot(None),
                Transaction.paid_date >= data_inicio
            ).group_by(
                func.date(Transaction.paid_date),
                Transaction.transaction_type
            ).all()
            
            if not transactions:
                return go.Figure()
            
            # Organiza dados
            periodos = sorted(list(set([t.periodo for t in transactions])))
            receitas = []
            despesas = []
            
            for p in periodos:
                receita = sum([t.total for t in transactions if t.periodo == p and t.transaction_type == "INCOME"])
                despesa = sum([t.total for t in transactions if t.periodo == p and t.transaction_type == "EXPENSE"])
                receitas.append(receita)
                despesas.append(despesa)
            
            # Cria gráfico
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=periodos,
                y=receitas,
                name="Receitas",
                marker_color="#27ae60"
            ))
            
            fig.add_trace(go.Bar(
                x=periodos,
                y=despesas,
                name="Despesas",
                marker_color="#e74c3c"
            ))
            
            fig.update_layout(
                barmode="group",
                xaxis_title="Período",
                yaxis_title="Valor (R$)",
                hovermode="x unified",
                template="plotly_white",
                height=400,
            )
            
            return fig
    
    except Exception as e:
        logger.error(f"Erro ao atualizar gráfico de fluxo: {e}")
        return go.Figure()


# ==========================================
# GRÁFICO CATEGORIAS
# ==========================================


@app.callback(
    Output("grafico-categorias", "figure"),
    Input("dashboard-periodo", "start_date"),
    Input("dashboard-periodo", "end_date"),
    Input("store-reload-dashboard", "data"),
    State("store-user-id", "data"),
)
def atualizar_grafico_categorias(start_date, end_date, reload_trigger, user_id):
    """Atualiza gráfico de despesas por categoria."""
    if not user_id:
        return go.Figure()
    
    try:
        # Converte datas
        if start_date:
            data_inicio = datetime.fromisoformat(start_date)
        else:
            data_inicio = datetime.now().replace(day=1)
        
        if end_date:
            data_fim = datetime.fromisoformat(end_date)
        else:
            data_fim = datetime.now()
        
        with get_db_session() as db:
            from database.models.category import Category
            
            # Query para despesas por categoria
            result = db.query(
                Category.name,
                Category.icon,
                func.sum(Transaction.base_amount).label("total")
            ).join(
                Transaction, Transaction.category_id == Category.id
            ).filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == "EXPENSE",
                Transaction.paid_date.isnot(None),
                Transaction.paid_date >= data_inicio,
                Transaction.paid_date <= data_fim
            ).group_by(
                Category.name,
                Category.icon
            ).order_by(
                func.sum(Transaction.base_amount).desc()
            ).limit(10).all()
            
            if not result:
                return go.Figure()
            
            # Prepara dados
            labels = [f"{r.icon or '📁'} {r.name}" for r in result]
            values = [r.total for r in result]
            
            # Cria gráfico de pizza
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.4,
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>R$ %{value:,.2f}<br>%{percent}<extra></extra>"
            )])
            
            fig.update_layout(
                title="Top 10 Despesas por Categoria",
                template="plotly_white",
                height=400,
            )
            
            return fig
    
    except Exception as e:
        logger.error(f"Erro ao atualizar gráfico de categorias: {e}")
        return go.Figure()
