"""
Callbacks da página de Investimentos.
Padrão de segurança P0: user_id derivado exclusivamente do JWT via resolve_user().
Nunca usar store-user-id como autoridade.
"""

import dash_bootstrap_components as dbc
from dash import Input, Output, State, ctx, html, no_update

from app import app
from config.logging_config import app_logger
from database.connection import get_db_session
from middleware.auth_context import resolve_user
from middleware.rate_limiter import client_ip, hit
from services.investment_service import (
    InsufficientFundsError,
    InsufficientPositionError,
    InvestmentService,
    InvestmentValidationError,
)
from utils.exceptions import AuthenticationError


def _fmt_brl(value) -> str:
    from decimal import Decimal as _D

    amount = value if isinstance(value, _D) else _D(str(value or 0))
    return f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ─── 1. Carregar carteira ─────────────────────────────────────────────────────


@app.callback(
    Output("invest-portfolio-table", "children"),
    Input("auth-store", "data"),
    Input("store-reload-dashboard", "data"),
    prevent_initial_call=True,
)
def load_portfolio(auth_data, _reload):
    """Carrega posições derivadas do InvestmentService com user_id do JWT."""
    try:
        user_id = resolve_user(auth_data)
        with get_db_session() as db:
            svc = InvestmentService(db)
            positions = svc.get_portfolio_position(user_id)

        if not positions:
            return html.Div(
                [html.I(className="bi bi-inbox me-2"), "Nenhuma posição encontrada."],
                className="text-muted py-4 text-center",
            )

        rows = []
        for p in positions:
            rows.append(
                html.Tr(
                    [
                        html.Td(p.ticker),
                        html.Td(p.name),
                        html.Td(f"{p.quantity:.8f}"),
                        html.Td(_fmt_brl(p.avg_price)),
                        html.Td(_fmt_brl(p.total_cost)),
                    ]
                )
            )

        return dbc.Table(
            [
                html.Thead(
                    html.Tr(
                        [
                            html.Th("Ticker"),
                            html.Th("Ativo"),
                            html.Th("Qtd"),
                            html.Th("PM"),
                            html.Th("Custo"),
                        ]
                    )
                ),
                html.Tbody(rows),
            ],
            bordered=True,
            hover=True,
            responsive=True,
        )

    except AuthenticationError as e:
        return dbc.Alert(str(e), color="warning", dismissable=True)
    except Exception as e:
        app_logger.error(f"Erro ao carregar carteira: {e}")
        return dbc.Alert("Não foi possível carregar a carteira.", color="danger", dismissable=True)


# ─── 2. Abrir/fechar modal ────────────────────────────────────────────────────


@app.callback(
    Output("invest-operation-modal", "is_open"),
    Output("invest-edit-id", "data", allow_duplicate=True),
    Input("invest-btn-new", "n_clicks"),
    Input("invest-btn-cancel", "n_clicks"),
    Input("invest-btn-save", "n_clicks"),
    State("invest-operation-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_invest_modal(n_new, n_cancel, n_save, is_open):
    trigger = ctx.triggered_id
    if trigger == "invest-btn-new":
        return True, None
    if trigger in ("invest-btn-cancel", "invest-btn-save"):
        return False, None
    return no_update, no_update


# ─── 3. Salvar operação ───────────────────────────────────────────────────────


@app.callback(
    Output("invest-modal-alert", "children"),
    Output("invest-modal-alert", "is_open"),
    Output("invest-alert", "children"),
    Output("invest-alert", "is_open"),
    Input("invest-btn-save", "n_clicks"),
    State("auth-store", "data"),
    State("invest-edit-id", "data"),
    State("invest-op-type", "value"),
    State("invest-asset-select", "value"),
    State("invest-account-select", "value"),
    State("invest-qty", "value"),
    State("invest-price", "value"),
    State("invest-fees", "value"),
    State("invest-date", "date"),
    State("invest-notes", "value"),
    prevent_initial_call=True,
)
def save_investment_operation(
    n_clicks,
    auth_data,
    edit_id,
    op_type,
    asset_id,
    account_id,
    qty,
    price,
    fees,
    op_date,
    notes,
):
    if not n_clicks:
        return no_update, no_update, no_update, no_update

    # Rate limit por IP (exemplo P1)
    allowed, retry_after = hit("invest.op", client_ip(), limit=30, window_seconds=60)
    if not allowed:
        msg = f"Taxa de requisições excedida. Tente novamente em {retry_after}s."
        return dbc.Alert(msg, color="warning"), True, no_update, no_update

    try:
        user_id = resolve_user(auth_data)

        # Validações mínimas de formulário
        if not asset_id or not account_id or not qty or not price:
            raise InvestmentValidationError("Preencha todos os campos obrigatórios.")

        from datetime import date
        from decimal import Decimal

        op_date_obj = date.fromisoformat(op_date) if op_date else date.today()
        qty_dec = Decimal(str(qty)) if qty is not None else None
        price_dec = Decimal(str(price)) if price is not None else None
        fees_dec = Decimal(str(fees)) if fees is not None else None

        with get_db_session() as db:
            svc = InvestmentService(db)
            # Esqueleto: escolher método conforme op_type
            # BUY / SELL / DIVIDEND / SPLIT
            if op_type == "BUY":
                svc.buy(
                    asset_id=int(asset_id),
                    user_id=user_id,
                    quantity=qty_dec,
                    price_per_unit=price_dec,
                    account_id=int(account_id),
                    operation_date=op_date_obj,
                    fees=fees_dec or Decimal("0"),
                    notes=notes,
                )
                msg = "Compra registrada com sucesso."
            elif op_type == "SELL":
                svc.sell(
                    asset_id=int(asset_id),
                    user_id=user_id,
                    quantity=qty_dec,
                    price_per_unit=price_dec,
                    account_id=int(account_id),
                    operation_date=op_date_obj,
                    fees=fees_dec or Decimal("0"),
                    notes=notes,
                )
                msg = "Venda registrada com sucesso."
            elif op_type == "DIVIDEND":
                svc.record_dividend(
                    asset_id=int(asset_id),
                    user_id=user_id,
                    amount=qty_dec,  # no UI, qty usado como valor do provento no esqueleto
                    account_id=int(account_id),
                    operation_date=op_date_obj,
                    notes=notes,
                )
                msg = "Provento registrado com sucesso."
            elif op_type == "SPLIT":
                svc.apply_split(
                    asset_id=int(asset_id),
                    user_id=user_id,
                    factor=qty_dec,
                    operation_date=op_date_obj,
                    notes=notes,
                )
                msg = "Split registrado com sucesso."
            else:
                raise InvestmentValidationError("Tipo de operação inválido.")

        alert = dbc.Alert(msg, color="success", dismissable=True)
        return "", False, alert, True

    except AuthenticationError as e:
        return dbc.Alert(str(e), color="warning"), True, no_update, no_update
    except InsufficientFundsError as e:
        return dbc.Alert(str(e), color="danger"), True, no_update, no_update
    except InsufficientPositionError as e:
        return dbc.Alert(str(e), color="danger"), True, no_update, no_update
    except InvestmentValidationError as e:
        return dbc.Alert(str(e), color="warning"), True, no_update, no_update
    except Exception as e:
        app_logger.error(f"Erro ao salvar operação de investimento: {e}")
        return (
            dbc.Alert("Erro inesperado ao salvar operação.", color="danger"),
            True,
            no_update,
            no_update,
        )
