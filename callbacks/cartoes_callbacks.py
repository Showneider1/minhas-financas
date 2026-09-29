"""Callbacks da página de Cartões de Crédito."""

from decimal import Decimal, InvalidOperation

import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, ctx, html, no_update

from app import app
from config.logging_config import app_logger
from database.connection import get_db_session
from database.enums import AccountType
from database.models.credit_card import CreditCard
from middleware.auth_context import resolve_user
from services.account_service import AccountService
from services.credit_card_service import CreditCardError, CreditCardService
from utils.exceptions import AuthenticationError


def _fmt_brl(value) -> str:
    amount = value if isinstance(value, Decimal) else Decimal(str(value or 0))
    return f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@app.callback(
    Output("cartoes-list-container", "children"),
    Input("auth-store", "data"),
    Input("cartoes-reload-trigger", "data"),
    prevent_initial_call=True,
)
def load_credit_cards(auth_data, _reload):
    """Carrega os cartões do usuário logado."""
    try:
        user_id = resolve_user(auth_data)
    except AuthenticationError:
        return dbc.Alert("Sessão expirada — faça login novamente.", color="warning")

    try:
        with get_db_session() as db:
            service = CreditCardService(db)
            cards = (
                db.query(CreditCard)
                .filter(CreditCard.user_id == user_id, CreditCard.is_active.is_(True))
                .order_by(CreditCard.name.asc())
                .all()
            )

            if not cards:
                return html.Div(
                    [
                        html.I(
                            className=(
                                "bi bi-credit-card display-4 text-muted "
                                "d-block text-center mb-3 mt-4"
                            )
                        ),
                        html.P(
                            "Nenhum cartão cadastrado.",
                            className="text-center text-muted",
                        ),
                    ],
                    className="py-4",
                )

            items = []
            for card in cards:
                available = service.get_available_limit(user_id, card.id)
                used = Decimal(str(card.credit_limit or 0)) - available
                progress = (
                    float(used / Decimal(str(card.credit_limit or 1)) * 100)
                    if Decimal(str(card.credit_limit or 0)) > 0
                    else 0
                )
                items.append(
                    dbc.Col(
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    [
                                        html.I(
                                            className=("bi bi-credit-card-fill text-primary me-2")
                                        ),
                                        html.Span(card.name, className="fw-bold"),
                                    ],
                                    className="bg-white border-0 pb-0",
                                ),
                                dbc.CardBody(
                                    [
                                        html.P(
                                            [
                                                html.Small(
                                                    "Limite disponível",
                                                    className="text-muted d-block",
                                                ),
                                                html.Strong(
                                                    _fmt_brl(available),
                                                    className="text-success fs-5",
                                                ),
                                            ],
                                            className="mb-2",
                                        ),
                                        dbc.Progress(
                                            value=progress,
                                            color="warning",
                                            className="mb-3",
                                            style={"height": "6px"},
                                        ),
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    [
                                                        html.Small(
                                                            "Limite total",
                                                            className="text-muted d-block",
                                                        ),
                                                        html.Strong(_fmt_brl(card.credit_limit)),
                                                    ],
                                                    width=4,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Small(
                                                            "Fechamento",
                                                            className="text-muted d-block",
                                                        ),
                                                        html.Strong(f"Dia {card.closing_day}"),
                                                    ],
                                                    width=4,
                                                ),
                                                dbc.Col(
                                                    [
                                                        html.Small(
                                                            "Vencimento",
                                                            className="text-muted d-block",
                                                        ),
                                                        html.Strong(f"Dia {card.due_day}"),
                                                    ],
                                                    width=4,
                                                ),
                                            ],
                                            className="text-center",
                                        ),
                                    ],
                                    className="pt-2",
                                ),
                                dbc.CardFooter(
                                    dbc.Button(
                                        [
                                            html.I(className="bi bi-receipt me-1"),
                                            "Ver fatura",
                                        ],
                                        id={"type": "btn-ver-fatura", "index": card.id},
                                        color="primary",
                                        outline=True,
                                        size="sm",
                                        className="w-100",
                                    ),
                                    className="bg-white border-0 pt-0 pb-3",
                                ),
                            ],
                            className="shadow-sm border-0 h-100",
                        ),
                        width=12,
                        lg=4,
                        className="mb-3",
                    )
                )

            return dbc.Row(items)
    except Exception as exc:
        app_logger.error(f"Erro ao carregar cartões: {exc}")
        return dbc.Alert(
            "Não foi possível carregar os cartões.",
            color="danger",
            dismissable=True,
        )


@app.callback(
    Output("modal-credit-card", "is_open"),
    Output("credit-card-nome", "value"),
    Output("credit-card-limite", "value"),
    Output("credit-card-fechamento", "value"),
    Output("credit-card-vencimento", "value"),
    Output("credit-card-feedback", "children"),
    Input("btn-open-credit-card-modal", "n_clicks"),
    Input("btn-cancel-credit-card-modal", "n_clicks"),
    prevent_initial_call=True,
)
def toggle_credit_card_modal(n_open, n_cancel):
    """Abre e fecha o modal de novo cartão."""
    triggered = ctx.triggered_id

    if triggered == "btn-open-credit-card-modal" and n_open:
        return True, "", "", None, None, ""

    if triggered == "btn-cancel-credit-card-modal" and n_cancel:
        return False, no_update, no_update, no_update, no_update, ""

    return no_update, no_update, no_update, no_update, no_update, no_update


@app.callback(
    Output("credit-card-feedback", "children", allow_duplicate=True),
    Output("cartoes-feedback", "children"),
    Output("cartoes-feedback", "is_open"),
    Output("cartoes-reload-trigger", "data", allow_duplicate=True),
    Output("modal-credit-card", "is_open", allow_duplicate=True),
    Input("btn-save-credit-card-modal", "n_clicks"),
    State("credit-card-nome", "value"),
    State("credit-card-limite", "value"),
    State("credit-card-fechamento", "value"),
    State("credit-card-vencimento", "value"),
    State("auth-store", "data"),
    State("cartoes-reload-trigger", "data"),
    prevent_initial_call=True,
)
def create_credit_card(
    n_clicks,
    name,
    limit,
    closing_day,
    due_day,
    auth_data,
    reload_counter,
):
    """Cria um novo cartão de crédito."""
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update

    try:
        user_id = resolve_user(auth_data)

        if not (name or "").strip():
            raise CreditCardError("Informe o nome do cartão.")
        if limit in (None, ""):
            raise CreditCardError("Informe o limite do cartão.")
        if closing_day in (None, ""):
            raise CreditCardError("Informe o dia de fechamento.")
        if due_day in (None, ""):
            raise CreditCardError("Informe o dia de vencimento.")

        try:
            limit_decimal = Decimal(str(limit))
        except (InvalidOperation, ValueError):
            raise CreditCardError("Limite inválido.")

        closing_day_int = int(closing_day)
        due_day_int = int(due_day)
        if not (1 <= closing_day_int <= 31):
            raise CreditCardError("Dia de fechamento deve estar entre 1 e 31.")
        if not (1 <= due_day_int <= 31):
            raise CreditCardError("Dia de vencimento deve estar entre 1 e 31.")

        with get_db_session() as db:
            CreditCardService(db).create_credit_card(
                user_id=user_id,
                name=name.strip(),
                credit_limit=limit_decimal,
                closing_day=closing_day_int,
                due_day=due_day_int,
            )

        return (
            "",
            dbc.Alert(
                f'Cartão "{name.strip()}" criado com sucesso!',
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
    except CreditCardError as exc:
        return (
            dbc.Alert(str(exc), color="warning", dismissable=True),
            no_update,
            no_update,
            no_update,
            True,
        )
    except Exception as exc:
        app_logger.error(f"Erro ao criar cartão: {exc}")
        return (
            dbc.Alert(
                "Não foi possível criar o cartão.",
                color="danger",
                dismissable=True,
            ),
            no_update,
            no_update,
            no_update,
            True,
        )


# ─── Modal de Fatura ─────────────────────────────────────────────────────────
@app.callback(
    Output("modal-fatura", "is_open"),
    Output("fatura-card-id", "data"),
    Input({"type": "btn-ver-fatura", "index": ALL}, "n_clicks"),
    State("modal-fatura", "is_open"),
    prevent_initial_call=True,
)
def abrir_modal_fatura(clicks, is_open):
    """Abre o modal de fatura do cartão clicado."""
    triggered = ctx.triggered_id
    if not isinstance(triggered, dict) or triggered.get("type") != "btn-ver-fatura":
        return no_update, no_update
    if not any(clicks):
        return no_update, no_update
    return True, triggered["index"]


@app.callback(
    Output("modal-fatura", "is_open", allow_duplicate=True),
    Input("btn-fechar-fatura", "n_clicks"),
    prevent_initial_call=True,
)
def fechar_modal_fatura(n_clicks):
    """Fecha o modal de fatura."""
    return False if n_clicks else no_update


@app.callback(
    Output("fatura-container", "children"),
    Output("fatura-conta-origem", "options"),
    Output("btn-pagar-fatura", "disabled"),
    Output("fatura-feedback", "children"),
    Input("modal-fatura", "is_open"),
    Input("fatura-mes", "value"),
    Input("fatura-ano", "value"),
    Input("fatura-card-id", "data"),
    Input("auth-store", "data"),
    Input("cartoes-reload-trigger", "data"),
    prevent_initial_call=True,
)
def carregar_fatura(is_open, month, year, card_id, auth_data, _reload):
    """Carrega a fatura do mês selecionado."""
    if not is_open or not card_id or not auth_data:
        return no_update, no_update, no_update, no_update

    try:
        user_id = resolve_user(auth_data)
    except AuthenticationError:
        return (
            dbc.Alert("Sessão expirada — faça login novamente.", color="warning"),
            [],
            True,
            no_update,
        )

    try:
        with get_db_session() as db:
            accounts = [
                account
                for account in AccountService(db).get_user_accounts(user_id)
                if account.account_type != AccountType.CREDIT_CARD
            ]
            account_options = [{"label": account.name, "value": account.id} for account in accounts]

            invoice = CreditCardService(db).get_invoice(
                user_id=user_id,
                credit_card_id=int(card_id),
                month=int(month),
                year=int(year),
            )
            card = invoice["card"]
            status = str(invoice["status"])
            status_color = {
                "Aberta": "info",
                "Fechada": "warning",
                "Paga": "success",
                "Vazia": "secondary",
            }.get(status, "secondary")

            summary_cards = dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.Small("Total da fatura", className="text-muted"),
                                    html.H5(
                                        _fmt_brl(invoice["total"]),
                                        className="fw-bold mb-0",
                                    ),
                                ]
                            ),
                            className="shadow-sm border-0",
                        ),
                        width=6,
                        lg=3,
                        className="mb-2",
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.Small("Em aberto", className="text-muted"),
                                    html.H5(
                                        _fmt_brl(invoice["unpaid_total"]),
                                        className="fw-bold text-danger mb-0",
                                    ),
                                ]
                            ),
                            className="shadow-sm border-0",
                        ),
                        width=6,
                        lg=3,
                        className="mb-2",
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.Small("Compras futuras", className="text-muted"),
                                    html.H5(
                                        _fmt_brl(invoice["future_total"]),
                                        className="fw-bold text-warning mb-0",
                                    ),
                                ]
                            ),
                            className="shadow-sm border-0",
                        ),
                        width=6,
                        lg=3,
                        className="mb-2",
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.Small("Limite disponível", className="text-muted"),
                                    html.H5(
                                        _fmt_brl(invoice["available_limit"]),
                                        className="fw-bold text-success mb-0",
                                    ),
                                ]
                            ),
                            className="shadow-sm border-0",
                        ),
                        width=6,
                        lg=3,
                        className="mb-2",
                    ),
                ],
                className="mb-3",
            )

            if not invoice["transactions"]:
                table = html.Div(
                    [
                        html.I(className="bi bi-receipt-cutoff display-6 text-muted"),
                        html.P(
                            "Nenhuma compra nesta fatura.",
                            className="text-muted mt-2",
                        ),
                    ],
                    className="text-center py-4",
                )
            else:
                rows = []
                for transaction in invoice["transactions"]:
                    paid = transaction.paid_date is not None
                    rows.append(
                        html.Tr(
                            [
                                html.Td(transaction.due_date.strftime("%d/%m/%Y")),
                                html.Td(transaction.description),
                                html.Td(
                                    f"{transaction.installment_number}/"
                                    f"{transaction.total_installments}"
                                ),
                                html.Td(_fmt_brl(transaction.base_amount), className="text-end"),
                                html.Td(
                                    dbc.Badge(
                                        "Pago" if paid else "Pendente",
                                        color="success" if paid else "warning",
                                        pill=True,
                                    ),
                                    className="text-center",
                                ),
                            ]
                        )
                    )

                table = dbc.Table(
                    [
                        html.Thead(
                            html.Tr(
                                [
                                    html.Th("Vencimento"),
                                    html.Th("Descrição"),
                                    html.Th("Parcela"),
                                    html.Th("Valor", className="text-end"),
                                    html.Th("Status", className="text-center"),
                                ]
                            )
                        ),
                        html.Tbody(rows),
                    ],
                    hover=True,
                    striped=True,
                    responsive=True,
                    className="align-middle",
                )

            closing_label = invoice["closing_date"].strftime("%d/%m/%Y")
            due_label = invoice["due_date"].strftime("%d/%m/%Y")

            content = html.Div(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H5(
                                        [
                                            html.I(
                                                className=(
                                                    "bi bi-credit-card-fill me-2 text-primary"
                                                )
                                            ),
                                            card.name,
                                        ],
                                        className="fw-bold",
                                    ),
                                    html.Small(
                                        f"Fechamento: {closing_label} | Vencimento: {due_label}",
                                        className="text-muted",
                                    ),
                                ],
                                width=True,
                            ),
                            dbc.Col(
                                dbc.Badge(
                                    status,
                                    color=status_color,
                                    pill=True,
                                    className="fs-6",
                                ),
                                width="auto",
                                className="d-flex align-items-center justify-content-end",
                            ),
                        ],
                        align="center",
                        className="mb-3",
                    ),
                    summary_cards,
                    table,
                ]
            )

            pay_disabled = status == "Paga" or invoice["unpaid_total"] <= 0 or not account_options

            return content, account_options, pay_disabled, ""
    except AuthenticationError:
        return (
            dbc.Alert("Sessão expirada — faça login novamente.", color="warning"),
            [],
            True,
            no_update,
        )
    except Exception as exc:
        app_logger.error(f"Erro ao carregar fatura: {exc}")
        return (
            dbc.Alert(
                "Não foi possível carregar a fatura.",
                color="danger",
                dismissable=True,
            ),
            [],
            True,
            no_update,
        )


@app.callback(
    Output("fatura-feedback", "children", allow_duplicate=True),
    Output("cartoes-reload-trigger", "data", allow_duplicate=True),
    Output("store-reload-dashboard", "data", allow_duplicate=True),
    Input("btn-pagar-fatura", "n_clicks"),
    State("fatura-card-id", "data"),
    State("fatura-mes", "value"),
    State("fatura-ano", "value"),
    State("fatura-conta-origem", "value"),
    State("auth-store", "data"),
    State("cartoes-reload-trigger", "data"),
    State("store-reload-dashboard", "data"),
    prevent_initial_call=True,
)
def pagar_fatura(
    n_clicks,
    card_id,
    month,
    year,
    source_account_id,
    auth_data,
    cartoes_reload,
    dashboard_reload,
):
    """Paga a fatura selecionada com a conta de origem escolhida."""
    if not n_clicks:
        return no_update, no_update, no_update

    try:
        user_id = resolve_user(auth_data)
        if not card_id:
            raise CreditCardError("Selecione um cartão.")
        if not source_account_id:
            raise CreditCardError("Selecione a conta de origem.")

        with get_db_session() as db:
            CreditCardService(db).pay_invoice(
                user_id=user_id,
                credit_card_id=int(card_id),
                month=int(month),
                year=int(year),
                source_account_id=int(source_account_id),
            )

        return (
            dbc.Alert(
                "Fatura paga com sucesso!",
                color="success",
                dismissable=True,
                duration=4000,
            ),
            (cartoes_reload or 0) + 1,
            (dashboard_reload or 0) + 1,
        )
    except AuthenticationError as exc:
        return (
            dbc.Alert(str(exc), color="warning", dismissable=True),
            no_update,
            no_update,
        )
    except CreditCardError as exc:
        return (
            dbc.Alert(str(exc), color="warning", dismissable=True),
            no_update,
            no_update,
        )
    except Exception as exc:
        app_logger.error(f"Erro ao pagar fatura: {exc}")
        return (
            dbc.Alert(
                "Não foi possível pagar a fatura.",
                color="danger",
                dismissable=True,
            ),
            no_update,
            no_update,
        )
