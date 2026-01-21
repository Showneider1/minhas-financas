"""
Callbacks OTIMIZADOS da página de dashboard.
"""
from dash import Input, Output, State, html
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime, date
from app import app
from database.connection import get_db_session
from services.dashboard_service import DashboardService
from database.models.category import TransactionType
from config.logging_config import app_logger

# ==========================================
# ATUALIZAÇÃO GERAL (KPIS)
# ==========================================
@app.callback(
    Output("kpi-saldo", "children"),
    Output("kpi-receita", "children"),
    Output("kpi-despesa", "children"),
    Output("kpi-receita-info", "children"),
    Output("kpi-despesa-info", "children"),
    Input("dashboard-periodo", "start_date"),
    Input("dashboard-periodo", "end_date"),
    Input("store-reload-dashboard", "data"),
    Input("btn-update-dashboard", "n_clicks"),
    State("store-user-id", "data"),
)
def update_kpis(start_date, end_date, _, __, user_id):
    if not user_id:
        return "R$ 0,00", "R$ 0,00", "R$ 0,00", "-", "-"

    try:
        dt_start = datetime.fromisoformat(start_date).date() if start_date else date.today().replace(day=1)
        dt_end = datetime.fromisoformat(end_date).date() if end_date else date.today()
    except:
        dt_start = date.today().replace(day=1)
        dt_end = date.today()

    try:
        with get_db_session() as db:
            service = DashboardService(db)
            data = service.get_overview(user_id, dt_start, dt_end)
            
            saldo_str = f"R$ {data['saldo']['contas']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            receita_val = data['receitas']['pagas']
            receita_str = f"R$ {receita_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            receita_info = f"Pendentes: R$ {data['receitas']['pendentes']:,.2f}"
            
            despesa_val = data['despesas']['pagas']
            despesa_str = f"R$ {despesa_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            despesa_info = f"Pendentes: R$ {data['despesas']['pendentes']:,.2f}"
            
            return saldo_str, receita_str, despesa_str, receita_info, despesa_info

    except Exception as e:
        app_logger.error(f"Erro ao atualizar KPIs: {e}")
        return "Erro", "Erro", "Erro", "-", "-"

# ==========================================
# GRÁFICOS E TABELA
# ==========================================
@app.callback(
    Output("grafico-fluxo-caixa", "figure"),
    Output("grafico-categorias", "figure"),
    Output("tabela-proximos-vencimentos", "children"),
    Input("dashboard-periodo", "start_date"),
    Input("dashboard-periodo", "end_date"),
    Input("store-reload-dashboard", "data"),
    State("store-user-id", "data"),
)
def update_charts_and_table(start_date, end_date, _, user_id):
    if not user_id:
        return go.Figure(), go.Figure(), html.P("Sem dados")

    try:
        dt_start = datetime.fromisoformat(start_date).date() if start_date else date.today().replace(day=1)
        dt_end = datetime.fromisoformat(end_date).date() if end_date else date.today()
    except:
        dt_start = date.today().replace(day=1)
        dt_end = date.today()

    fig1 = go.Figure()
    fig2 = go.Figure()
    table = html.Div()

    try:
        with get_db_session() as db:
            service = DashboardService(db)
            
            # 1. Gráfico de Evolução
            evolution = service.get_monthly_evolution(user_id, months=6)
            months = [item['month'] for item in evolution['receitas']]
            receitas = [item['value'] for item in evolution['receitas']]
            despesas = [item['value'] for item in evolution['despesas']]
            
            fig1.add_trace(go.Bar(x=months, y=receitas, name='Receitas', marker_color='#2ecc71'))
            fig1.add_trace(go.Bar(x=months, y=despesas, name='Despesas', marker_color='#e74c3c'))
            fig1.update_layout(barmode='group', margin=dict(l=20, r=20, t=30, b=20), legend=dict(orientation="h"), template="plotly_white")

            # 2. Gráfico de Categorias
            cats = service.get_category_breakdown(user_id, TransactionType.EXPENSE, dt_start, dt_end)
            if cats:
                labels = [f"{c['icon'] or ''} {c['name']}" for c in cats]
                values = [c['total'] for c in cats]
                fig2.add_trace(go.Pie(labels=labels, values=values, hole=.5))
                fig2.update_layout(margin=dict(l=20, r=20, t=30, b=20), showlegend=False, template="plotly_white")
            else:
                fig2.add_annotation(text="Sem despesas no período", showarrow=False)

            # 3. Tabela de Próximos Vencimentos
            upcoming = service.get_upcoming_expenses(user_id, limit=5)
            
            if not upcoming:
                table = html.Div([
                    html.I(className="bi bi-check-circle fs-1 text-success mb-2"),
                    html.P("Tudo em dia!", className="text-muted")
                ], className="text-center py-4")
            else:
                rows = []
                for t in upcoming:
                    val_fmt = f"R$ {t.base_amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    date_fmt = t.due_date.strftime("%d/%m")
                    cat_icon = t.category.icon if t.category else "📝"
                    
                    rows.append(html.Tr([
                        html.Td(html.Span(date_fmt, className="badge bg-light text-dark border")),
                        html.Td([
                            html.Div(t.description, className="fw-bold text-truncate", style={"maxWidth": "150px"}),
                            html.Small(f"{cat_icon} {t.category.name if t.category else 'Geral'}", className="text-muted")
                        ]),
                        html.Td(val_fmt, className="text-end fw-bold text-danger"),
                    ]))
                
                table = dbc.Table([html.Tbody(rows)], borderless=True, hover=True, responsive=True, className="align-middle mb-0")

    except Exception as e:
        app_logger.error(f"Erro nos gráficos/tabela: {e}")

    return fig1, fig2, table