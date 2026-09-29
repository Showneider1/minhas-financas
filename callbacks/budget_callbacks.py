"""Callbacks da página de Orçamentos."""

from datetime import date
from decimal import Decimal, InvalidOperation

import dash_bootstrap_components as dbc
from dash import Input, Output, State, ctx, html, no_update

from app import app
from config.logging_config import app_logger
from database.connection import get_db_session
from database.enums import TransactionType
from middleware.auth_context import resolve_user
from services.budget_service import BudgetService
from services.category_service import CategoryService
from utils.exceptions import AuthenticationError


def _fmt_brl(value) -> str:
    amount = value if isinstance(value, Decimal) else Decimal(str(value or 0))
    return f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@app.callback(
    Output("budget-category", "options"),
    Output("budget-list-container", "children"),
    Output("budget-feedback", "children"),
    Output("budget-feedback", "is_open"),
    Input("url", "pathname"),
    Input("auth-store", "data"),
    Input("budget-month", "value"),
    Input("budget-year", "value"),
    Input("budgets-reload-trigger", "data"),
    prevent_initial_call=True,
)
def load_budgets(
    pathname,
    auth_data,
    month,
    year,
    _reload,
):
    """Carrega categorias e o progresso dos orçamentos."""
    if pathname != "/metas":
        return no_update, no_update, no_update, no_update
    if not auth_data:
        return [], html.Div(), no_update, no_update

    try:
        user_id = resolve_user(auth_data)
        with get_db_session() as db:
            categories = CategoryService(db).get_available_categories(
                user_id, TransactionType.EXPENSE
            )
            category_options = [
                {"label": f"{category.icon} {category.name}", "value": category.id}
                for category in categories
                if category.transaction_type == TransactionType.EXPENSE
            ]

            service = BudgetService(db)
            progress = service.get_budget_progress(
                user_id,
                int(month or date.today().month),
                int(year or date.today().year),
            )

        if not progress:
            content = html.Div(
                [
                    html.I(className="bi bi-wallet2 display-4 text-muted"),
                    html.P(
                        "Nenhum orçamento definido para este período.",
                        className="text-muted mt-2",
                    ),
                ],
                className="text-center py-5",
            )
        else:
            cards = []
            for item in progress:
                if item.percentage > 90:
                    progress_color = "danger"
                    text_color = "text-danger"
                elif item.percentage >= 76:
                    progress_color = "warning"
                    text_color = "text-warning"
                else:
                    progress_color = "success"
                    text_color = "text-success"

                cards.append(
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.I(className=f"{item.category_icon} me-2"),
                                        html.Strong(item.category_name),
                                    ],
                                    className="bg-white border-0",
                                ),
                                dbc.CardBody(
                                    [
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        html.Small(
                                                            "Limite",
                                                            className="text-muted d-block",
                                                        ),
                                                        html.Strong(_fmt_brl(item.amount_limit)),
                                                    ],
                                                    width=4,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Small(
                                                            "Gasto",
                                                            className="text-muted d-block",
                                                        ),
                                                        html.Strong(
                                                            _fmt_brl(item.spent),
                                                            className=text_color,
                                                        ),
                                                    ],
                                                    width=4,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Small(
                                                            "% usado",
                                                            className="text-muted d-block",
                                                        ),
                                                        html.Strong(
                                                            f"{item.percentage:.1f}%",
                                                            className=text_color,
                                                        ),
                                                    ],
                                                    width=4,
                                                ),
                                            ],
                                            className="mb-3 text-center",
                                        ),
                                        dbc.Progress(
                                            value=min(item.percentage, 100),
                                            color=progress_color,
                                            style={"height": "10px"},
                                        ),
                                    ],
                                    className="pt-2",
                                ),
                            ],
                            className="shadow-sm border-0 h-100",
                        ),
                        width=12,
                        lg=4,
                        className="mb-3",
                    )
                )

            content = dbc.Row(cards)

        return category_options, content, "", False

    except AuthenticationError as exc:
        return (
            [],
            html.Div(),
            dbc.Alert(str(exc), color="warning", dismissable=True),
            True,
        )
    except Exception as exc:
        app_logger.error(f"Erro ao carregar orçamentos: {exc}")
        return (
            [],
            html.Div(),
            dbc.Alert(
                "Não foi possível carregar os orçamentos.",
                color="danger",
                dismissable=True,
            ),
            True,
        )


@app.callback(
    Output("budget-modal", "is_open"),
    Output("budget-category", "value"),
    Output("budget-amount", "value"),
    Output("budget-modal-feedback", "children"),
    Input("btn-open-budget-modal", "n_clicks"),
    Input("btn-cancel-budget-modal", "n_clicks"),
    prevent_initial_call=True,
)
def toggle_budget_modal(n_open, n_cancel):
    """Abre e fecha o modal de novo orçamento."""
    triggered = ctx.triggered_id

    if triggered == "btn-open-budget-modal" and n_open:
        return True, None, "", ""

    if triggered == "btn-cancel-budget-modal" and n_cancel:
        return False, no_update, no_update, ""

    return no_update, no_update, no_update, no_update


@app.callback(
    Output("budget-modal-feedback", "children", allow_duplicate=True),
    Output("budget-feedback", "children", allow_duplicate=True),
    Output("budget-feedback", "is_open", allow_duplicate=True),
    Output("budgets-reload-trigger", "data", allow_duplicate=True),
    Output("budget-modal", "is_open", allow_duplicate=True),
    Input("btn-save-budget-modal", "n_clicks"),
    State("auth-store", "data"),
    State("budget-category", "value"),
    State("budget-amount", "value"),
    State("budget-month", "value"),
    State("budget-year", "value"),
    State("budgets-reload-trigger", "data"),
    prevent_initial_call=True,
)
def save_budget(
    n_clicks,
    auth_data,
    category_id,
    amount,
    month,
    year,
    reload_counter,
):
    """Salva ou atualiza um orçamento."""
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update

    try:
        user_id = resolve_user(auth_data)

        if not category_id:
            raise ValueError("Selecione a categoria.")
        if amount in (None, ""):
            raise ValueError("Informe o valor limite.")

        try:
            amount_decimal = Decimal(str(amount))
        except (InvalidOperation, ValueError):
            raise ValueError("Valor limite inválido.")

        with get_db_session() as db:
            BudgetService(db).set_budget(
                user_id=user_id,
                category_id=int(category_id),
                month=int(month or date.today().month),
                year=int(year or date.today().year),
                amount_limit=amount_decimal,
            )

        return (
            "",
            dbc.Alert(
                "Orçamento salvo com sucesso!",
                color="success",
                dismissable=True,
                duration=4000,
            ),
            True,
            (reload_counter or 0) + 1,
            False,
        )

    except AuthenticationError as exc:
        return (
            dbc.Alert(str(exc), color="warning", dismissable=True),
            no_update,
            no_update,
            no_update,
            True,
        )
    except ValueError as exc:
        return (
            dbc.Alert(str(exc), color="warning", dismissable=True),
            no_update,
            no_update,
            no_update,
            True,
        )
    except Exception as exc:
        app_logger.error(f"Erro ao salvar orçamento: {exc}")
        return (
            dbc.Alert(
                "Não foi possível salvar o orçamento.",
                color="danger",
                dismissable=True,
            ),
            no_update,
            no_update,
            no_update,
            True,
        )
