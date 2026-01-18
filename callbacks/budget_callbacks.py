from dash import Input, Output, State, no_update, html
import dash_bootstrap_components as dbc
from app import app
from database.connection import get_db_session
from services.category_service import CategoryService
from services.budget_service import BudgetService
from schemas.budget_schema import BudgetCreate
from database.models.category import TransactionType
from datetime import datetime

# ==========================================
# ABRIR/FECHAR MODAL E CARREGAR CATEGORIAS
# ==========================================
@app.callback(
    Output("modal-budget", "is_open"),
    Output("select-budget-category", "options"),
    Input("btn-open-budget", "n_clicks"),
    Input("btn-close-budget", "n_clicks"),
    Input("btn-save-budget", "n_clicks"),
    State("modal-budget", "is_open"),
    State("store-user-id", "data"),
    prevent_initial_call=True,
)
def toggle_budget_modal(n_open, n_close, n_save, is_open, user_id):
    import dash
    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update
        
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if trigger_id == "btn-close-budget":
        return False, no_update

    if trigger_id == "btn-open-budget":
        if not user_id:
            return False, []
            
        with get_db_session() as db:
            cat_service = CategoryService(db)
            categories = cat_service.get_available_categories(user_id, TransactionType.EXPENSE)
            options = [{"label": f"{c.icon or '📁'} {c.name}", "value": c.id} for c in categories]
            return True, options
            
    return is_open, no_update

# ==========================================
# SALVAR META
# ==========================================
@app.callback(
    Output("budget-feedback", "children"),
    Output("store-reload-dashboard", "data", allow_duplicate=True),
    Input("btn-save-budget", "n_clicks"),
    State("select-budget-category", "value"),
    State("input-budget-amount", "value"),
    State("store-user-id", "data"),
    prevent_initial_call=True,
)
def save_budget(n_clicks, category_id, amount, user_id):
    if not n_clicks:
        return no_update, no_update
        
    if not category_id or not amount:
        return dbc.Alert("Preencha todos os campos!", color="warning", duration=3000), no_update
        
    try:
        with get_db_session() as db:
            service = BudgetService(db)
            data = BudgetCreate(category_id=int(category_id), amount=float(amount))
            service.create_or_update_budget(user_id, data)
            
        return dbc.Alert("✅ Meta definida com sucesso!", color="success", duration=3000), True
        
    except Exception as e:
        return dbc.Alert(f"Erro: {e}", color="danger"), no_update

# ==========================================
# RENDERIZAR BARRAS DE PROGRESSO (NOVO)
# ==========================================
@app.callback(
    Output("container-budgets", "children"),
    Input("store-reload-dashboard", "data"),
    Input("dashboard-periodo", "start_date"),
    Input("store-user-id", "data"),
)
def render_budgets(reload, start_date, user_id):
    if not user_id:
        return html.Div("Faça login para ver suas metas.", className="text-muted")

    try:
        # Usa a data do filtro para pegar o mês/ano de referência
        if start_date:
            date_obj = datetime.fromisoformat(start_date)
            month, year = date_obj.month, date_obj.year
        else:
            now = datetime.now()
            month, year = now.month, now.year

        with get_db_session() as db:
            service = BudgetService(db)
            budgets = service.get_user_budgets_status(user_id, month, year)
            
            if not budgets:
                return html.Div([
                    html.I(className="bi bi-inbox fs-4 text-muted mb-2"),
                    html.Br(),
                    "Nenhuma meta definida para este mês.",
                    html.Br(),
                    dbc.Button("Criar Primeira Meta", id="btn-create-first-budget", color="link", size="sm")
                ], className="text-center py-4")

            progress_bars = []
            
            for b in budgets:
                # Define cor baseada na % gasta
                if b.percentage >= 100:
                    color = "danger" # Estourou
                    label_class = "text-danger fw-bold"
                elif b.percentage >= 80:
                    color = "warning" # Alerta
                    label_class = "text-warning fw-bold"
                else:
                    color = "success" # Seguro
                    label_class = "text-success"

                bar = html.Div([
                    # Label Categoria e Valores
                    html.Div([
                        html.Span([
                            html.I(className="bi bi-tag-fill me-2 text-muted"),
                            f"{b.category_icon or ''} {b.category_name}"
                        ], className="fw-medium"),
                        html.Span([
                            html.Span(f"R$ {b.spent:,.2f}", className=label_class),
                            html.Span(f" / R$ {b.amount:,.2f}", className="text-muted ms-1 small")
                        ])
                    ], className="d-flex justify-content-between mb-1"),
                    
                    # Barra de Progresso
                    dbc.Progress(
                        value=b.percentage,
                        color=color,
                        className="mb-3",
                        style={"height": "10px"},
                        label=f"{int(b.percentage)}%" if b.percentage > 15 else "" # Só mostra label se couber
                    )
                ])
                progress_bars.append(bar)
            
            return progress_bars

    except Exception as e:
        import traceback
        traceback.print_exc()
        return html.Div(f"Erro ao carregar metas: {e}", className="text-danger")