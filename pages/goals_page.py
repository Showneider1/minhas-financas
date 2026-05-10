"""
Página de Metas Financeiras.
Permite criar, acompanhar e gerenciar metas de poupança do usuário.
"""
import dash_bootstrap_components as dbc
from dash import html, dcc
from database.models.goal import GoalCategory, GoalStatus

CATEGORY_LABELS = {
    GoalCategory.EMERGENCY_FUND: ("🛡️", "Reserva de Emergência"),
    GoalCategory.TRAVEL:         ("✈️",  "Viagem"),
    GoalCategory.EDUCATION:      ("📚", "Educação"),
    GoalCategory.PROPERTY:       ("🏠", "Imóvel"),
    GoalCategory.VEHICLE:        ("🚗", "Veículo"),
    GoalCategory.RETIREMENT:     ("🏖️", "Aposentadoria"),
    GoalCategory.INVESTMENT:     ("📈", "Investimento"),
    GoalCategory.OTHER:          ("🎯", "Outro"),
}

CATEGORY_OPTIONS = [
    {"label": f"{icon} {label}", "value": cat.value}
    for cat, (icon, label) in CATEGORY_LABELS.items()
]

STATUS_OPTIONS = [
    {"label": "✅ Ativas",     "value": GoalStatus.ACTIVE.value},
    {"label": "🏆 Concluídas", "value": GoalStatus.COMPLETED.value},
    {"label": "⏸️ Pausadas",   "value": GoalStatus.PAUSED.value},
    {"label": "❌ Canceladas", "value": GoalStatus.CANCELLED.value},
]

# ─── Modal: Criar / Editar Meta ──────────────────────────────────────────────
modal_goal = dbc.Modal(
    [
        dbc.ModalHeader(
            dbc.ModalTitle([
                html.I(className="bi bi-flag-fill me-2 text-warning"),
                html.Span("Meta Financeira", id="goal-modal-title"),
            ]),
            close_button=True,
        ),
        dbc.ModalBody([
            dcc.Store(id="goal-edit-id", data=None),

            dbc.Row([
                dbc.Col([
                    dbc.Label("Nome da Meta *", className="fw-bold"),
                    dbc.Input(
                        id="goal-input-name",
                        placeholder="Ex: Viagem para Europa, Reserva de Emergência...",
                        maxLength=200,
                    ),
                ]),
            ], className="mb-3"),

            dbc.Row([
                dbc.Col([
                    dbc.Label("Categoria *", className="fw-bold"),
                    dbc.Select(
                        id="goal-input-category",
                        options=CATEGORY_OPTIONS,
                        value=GoalCategory.OTHER.value,
                    ),
                ], width=6),
                dbc.Col([
                    dbc.Label("Valor Alvo (R$) *", className="fw-bold"),
                    dbc.InputGroup([
                        dbc.InputGroupText("R$"),
                        dbc.Input(
                            id="goal-input-target",
                            placeholder="0,00",
                            type="number",
                            min=0.01,
                            step=0.01,
                        ),
                    ]),
                ], width=6),
            ], className="mb-3"),

            dbc.Row([
                dbc.Col([
                    dbc.Label("Valor Já Acumulado (R$)", className="fw-bold"),
                    dbc.InputGroup([
                        dbc.InputGroupText("R$"),
                        dbc.Input(
                            id="goal-input-current",
                            placeholder="0,00",
                            type="number",
                            min=0,
                            step=0.01,
                            value=0,
                        ),
                    ]),
                ], width=6),
                dbc.Col([
                    dbc.Label("Prazo (Data Limite)", className="fw-bold"),
                    dcc.DatePickerSingle(
                        id="goal-input-deadline",
                        display_format="DD/MM/YYYY",
                        placeholder="Opcional",
                        className="d-block",
                        style={"width": "100%"},
                    ),
                ], width=6),
            ], className="mb-3"),

            dbc.Row([
                dbc.Col([
                    dbc.Label("Conta Vinculada (opcional)", className="fw-bold"),
                    dbc.Select(
                        id="goal-input-account",
                        options=[{"label": "Nenhuma", "value": ""}],
                        value="",
                    ),
                ]),
            ], className="mb-3"),

            dbc.Row([
                dbc.Col([
                    dbc.Label("Descrição (opcional)", className="fw-bold"),
                    dbc.Textarea(
                        id="goal-input-description",
                        placeholder="Descreva sua meta...",
                        rows=2,
                        maxLength=500,
                    ),
                ]),
            ], className="mb-3"),

            html.Div(id="goal-modal-feedback"),
        ]),
        dbc.ModalFooter([
            dbc.Button(
                [html.I(className="bi bi-x me-1"), "Cancelar"],
                id="goal-btn-cancel-modal",
                color="secondary", outline=True, n_clicks=0,
            ),
            dbc.Button(
                [html.I(className="bi bi-check2 me-1"), "Salvar Meta"],
                id="goal-btn-save",
                color="primary", n_clicks=0,
            ),
        ]),
    ],
    id="goal-modal",
    is_open=False,
    size="lg",
    backdrop="static",
)

# ─── Modal: Registrar Aporte ─────────────────────────────────────────────────
modal_contribution = dbc.Modal(
    [
        dbc.ModalHeader(
            dbc.ModalTitle([
                html.I(className="bi bi-cash-coin me-2 text-success"),
                "Registrar Aporte",
            ]),
            close_button=True,
        ),
        dbc.ModalBody([
            dcc.Store(id="goal-contribution-id", data=None),
            html.Div(id="goal-contribution-info", className="mb-3"),

            dbc.Row([
                dbc.Col([
                    dbc.Label("Tipo de Movimentação", className="fw-bold"),
                    dbc.RadioItems(
                        options=[
                            {
                                "label": html.Span([
                                    html.I(className="bi bi-plus-circle-fill text-success me-1"),
                                    " Depósito",
                                ]),
                                "value": "deposit",
                            },
                            {
                                "label": html.Span([
                                    html.I(className="bi bi-dash-circle-fill text-danger me-1"),
                                    " Retirada",
                                ]),
                                "value": "withdrawal",
                            },
                        ],
                        value="deposit",
                        id="goal-contribution-type",
                        inline=True,
                    ),
                ]),
            ], className="mb-3"),

            dbc.Row([
                dbc.Col([
                    dbc.Label("Valor (R$) *", className="fw-bold"),
                    dbc.InputGroup([
                        dbc.InputGroupText("R$"),
                        dbc.Input(
                            id="goal-contribution-amount",
                            placeholder="0,00",
                            type="number",
                            min=0.01,
                            step=0.01,
                        ),
                    ]),
                ]),
            ], className="mb-3"),

            html.Div(id="goal-contribution-feedback"),
        ]),
        dbc.ModalFooter([
            dbc.Button(
                [html.I(className="bi bi-x me-1"), "Cancelar"],
                id="goal-contribution-btn-cancel",
                color="secondary", outline=True, n_clicks=0,
            ),
            dbc.Button(
                [html.I(className="bi bi-check2 me-1"), "Confirmar Aporte"],
                id="goal-contribution-btn-save",
                color="success", n_clicks=0,
            ),
        ]),
    ],
    id="goal-contribution-modal",
    is_open=False,
    backdrop="static",
)

# ─── KPI Card Helper ─────────────────────────────────────────────────────────
def _kpi_card(icon, label, kpi_id, color):
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.Span(icon, className="me-2 fs-5"),
                html.Span(label, className="text-muted small fw-semibold"),
            ], className="mb-2"),
            html.H5(id=kpi_id, children="...", className=f"fw-bold mb-0 {color}"),
        ])
    ], className="shadow-sm border-0 h-100")

# ─── Layout Principal ─────────────────────────────────────────────────────────
layout = dbc.Container([
    dcc.Store(id="goals-reload-trigger", data=0),

    # Header
    dbc.Row([
        dbc.Col([
            html.H2(
                [html.I(className="bi bi-flag-fill me-2 text-warning"), "Metas Financeiras"],
                className="mb-0 fw-bold",
            ),
            html.P("Defina objetivos e acompanhe seu progresso", className="text-muted mb-0"),
        ], width=True),
        dbc.Col([
            dbc.Button(
                [html.I(className="bi bi-plus-circle-fill me-2"), "Nova Meta"],
                id="goal-btn-new",
                color="warning",
                className="fw-bold shadow-sm",
                n_clicks=0,
            ),
        ], width="auto", className="d-flex align-items-center"),
    ], align="center", className="mb-4"),

    # KPIs
    dbc.Row([
        dbc.Col(_kpi_card("🎯", "Metas Ativas",     "goals-kpi-total",    "text-dark"),    width=6, sm=3, className="mb-3"),
        dbc.Col(_kpi_card("💰", "Total Acumulado",  "goals-kpi-current",  "text-success"), width=6, sm=3, className="mb-3"),
        dbc.Col(_kpi_card("🏆", "Meta Total",       "goals-kpi-target",   "text-primary"), width=6, sm=3, className="mb-3"),
        dbc.Col(_kpi_card("📊", "Progresso Geral", "goals-kpi-progress", "text-warning"), width=6, sm=3, className="mb-3"),
    ], className="mb-2"),

    # Filtros
    dbc.Row([
        dbc.Col([
            dbc.InputGroup([
                dbc.InputGroupText(html.I(className="bi bi-funnel")),
                dbc.Select(
                    id="goals-filter-status",
                    options=[{"label": "Todos os Status", "value": ""}] + STATUS_OPTIONS,
                    value=GoalStatus.ACTIVE.value,
                ),
            ]),
        ], width=12, md=4, className="mb-3"),
        dbc.Col([
            dbc.InputGroup([
                dbc.InputGroupText(html.I(className="bi bi-tag")),
                dbc.Select(
                    id="goals-filter-category",
                    options=[{"label": "Todas as Categorias", "value": ""}] + CATEGORY_OPTIONS,
                    value="",
                ),
            ]),
        ], width=12, md=4, className="mb-3"),
    ], className="mb-2"),

    # Lista de metas
    dcc.Loading(
        html.Div(id="goals-list-container"),
        type="dot",
    ),

    # Modais
    modal_goal,
    modal_contribution,

], fluid=True, className="py-4 px-3")
