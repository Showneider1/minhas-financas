from dash import dcc
import dash_bootstrap_components as dbc
from datetime import date

def date_range_filter(id: str, start: date = None, end: date = None) -> dbc.Col:
    """Retorna um filtro de período com DatePickerRange"""
    return dbc.Col(
        [
            dbc.Label("Período", className="small fw-bold text-muted"),
            dcc.DatePickerRange(
                id=id,
                start_date=start or date.today().replace(day=1),
                end_date=end or date.today(),
                display_format="DD/MM/YYYY",
                className="w-100",
            ),
        ],
        md=4,
        className="mb-3",
    )

def dropdown_filter(id: str, label: str, options: list[dict], multi=True, placeholder="Todos") -> dbc.Col:
    """Retorna um filtro de dropdown"""
    return dbc.Col(
        [
            dbc.Label(label, className="small fw-bold text-muted"),
            dcc.Dropdown(
                id=id,
                options=options,
                multi=multi,
                placeholder=placeholder,
            ),
        ],
        md=4,
        className="mb-3",
    )

def status_filter(id: str) -> dbc.Col:
    """Filtro de status de pagamento"""
    return dbc.Col(
        [
            dbc.Label("Status", className="small fw-bold text-muted"),
            dcc.Dropdown(
                id=id,
                options=[
                    {"label": "Pago", "value": "pago"},
                    {"label": "Recebido", "value": "recebido"},
                    {"label": "Pendente", "value": "pendente"},
                ],
                multi=True,
                placeholder="Todos",
            ),
        ],
        md=4,
        className="mb-3",
    )
