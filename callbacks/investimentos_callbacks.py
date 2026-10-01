"""
Callbacks da página de Investimentos.
Padrão de segurança P0: user_id derivado exclusivamente do JWT via resolve_user().
Nunca usar store-user-id como autoridade.
"""

from decimal import Decimal, InvalidOperation

import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, ctx, html, no_update

from app import app
from config.logging_config import app_logger
from database.connection import get_db_session
from middleware.auth_context import resolve_user
from middleware.rate_limiter import client_ip, hit
from services.investment_rebalance_service import (
    InvestmentRebalanceService,
    RebalanceValidationError,
)
from services.investment_service import (
    InsufficientFundsError,
    InsufficientPositionError,
    InvestmentService,
    InvestmentValidationError,
)
from services.market_data_service import MarketDataService
from utils.exceptions import AuthenticationError


def _fmt_brl(value) -> str:
    amount = value if isinstance(value, Decimal) else Decimal(str(value or 0))
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
            summary = svc.get_position_summary(
                user_id,
                market_data_service=MarketDataService(db),
            )
            positions = summary["positions"]

        if not positions:
            return html.Div(
                [html.I(className="bi bi-inbox me-2"), "Nenhuma posição encontrada."],
                className="text-muted py-4 text-center",
            )

        rows = []
        for p in positions:
            profitability = p["profitability_pct"]
            profit_class = "text-success" if profitability >= 0 else "text-danger"
            rows.append(
                html.Tr(
                    [
                        html.Td(p["ticker"]),
                        html.Td(p["name"]),
                        html.Td(f"{p['quantity']:.8f}"),
                        html.Td(_fmt_brl(p["average_price"])),
                        html.Td(_fmt_brl(p["current_price"])),
                        html.Td(_fmt_brl(p["current_market_value"])),
                        html.Td(
                            f"{profitability:+.2f}%",
                            className=f"fw-bold {profit_class}",
                        ),
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
                            html.Th("Cotação Atual"),
                            html.Th("Saldo (R$)"),
                            html.Th("Rentabilidade (%)"),
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


# ─── 2. Atualizar cotações manualmente ────────────────────────────────────────


@app.callback(
    Output("invest-price-feedback", "children"),
    Input("btn-update-prices", "n_clicks"),
    State("auth-store", "data"),
    prevent_initial_call=True,
)
def update_market_prices(n_clicks, auth_data):
    """Busca cotações da carteira do usuário e atualiza o cache local."""
    if not n_clicks:
        return no_update

    try:
        user_id = resolve_user(auth_data)
        with get_db_session() as db:
            positions = InvestmentService(db).get_portfolio_position(user_id)
            tickers = sorted({position.ticker for position in positions})

            if not tickers:
                return dbc.Alert(
                    "Nenhuma posição encontrada para atualizar.",
                    color="info",
                    dismissable=True,
                )

            result = MarketDataService(db).update_prices_for_tickers(tickers)

        updated_count = len(result["updated"])
        failed_count = len(result["failed"])
        skipped_count = len(result["skipped"])

        if failed_count:
            color = "danger"
        elif updated_count == 0:
            color = "warning"
        else:
            color = "success"

        message = f"Cotações atualizadas: {updated_count} ativos."
        if skipped_count:
            message += f" Ignorados: {skipped_count}."
        if failed_count:
            message += f" Falhas: {failed_count}."

        return dbc.Alert(message, color=color, dismissable=True)

    except AuthenticationError as e:
        return dbc.Alert(str(e), color="warning", dismissable=True)
    except Exception as e:
        app_logger.error(f"Erro ao atualizar cotações: {e}")
        return dbc.Alert(
            "Não foi possível atualizar as cotações.",
            color="danger",
            dismissable=True,
        )


# ─── 3. Abrir/fechar modal ────────────────────────────────────────────────────


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


# ─── 4. Rebalanceamento Buy & Hold ─────────────────────────────────────────────


def _targets_editor(overview):
    """Inputs de % alvo por ativo (recriados a cada carregamento)."""
    items = overview["targets"]
    if not items:
        return html.Div(
            [html.I(className="bi bi-inbox me-2"), "Nenhum ativo cadastrado."],
            className="text-muted py-3",
        )
    return dbc.Row(
        [
            dbc.Col(
                dbc.InputGroup(
                    [
                        dbc.InputGroupText(item["ticker"]),
                        dbc.Input(
                            id={"type": "rebalance-target", "asset_id": item["asset_id"]},
                            type="number",
                            min=0,
                            max=100,
                            step=0.01,
                            value=float(item["target_pct"]),
                        ),
                        dbc.InputGroupText("%"),
                    ],
                    size="sm",
                ),
                width=12,
                sm=6,
                md=4,
                className="mb-2",
            )
            for item in items
        ]
    )


def _strategy_alert(overview):
    """Aviso quando os alvos não somam exatamente 100%."""
    total = overview["total_target_pct"]
    total_fmt = f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    remaining = overview["remaining_pct"]

    if total == 0:
        return dbc.Alert(
            [
                html.I(className="bi bi-exclamation-triangle-fill me-2"),
                html.Span(
                    [
                        "Carteira sem estratégia definida: nenhum ativo possui meta. ",
                        "Defina os percentuais-alvo para receber recomendações de compra.",
                    ]
                ),
            ],
            color="warning",
            className="mb-0",
        )
    if not overview["is_complete"]:
        return dbc.Alert(
            [
                html.I(className="bi bi-exclamation-triangle-fill me-2"),
                html.Span(
                    [
                        f"Metas somam {total_fmt}% — faltam {remaining:,.2f}% para 100%. "
                        "O aporte só é alocado nas fatias definidas; o restante fica "
                        "disponível em caixa.",
                    ]
                ),
            ],
            color="warning",
            className="mb-0",
        )
    return dbc.Alert(
        [
            html.I(className="bi bi-check-circle-fill me-2"),
            f"Estratégia definida: metas somam {total_fmt}%.",
        ],
        color="success",
        className="mb-0",
    )


def _plan_table(plan, summary):
    """Tabela de recomendações de compra."""
    if not plan:
        return html.Div(
            [
                html.I(className="bi bi-inbox me-2"),
                "Sem ativos com meta definida. Configure os percentuais-alvo acima.",
            ],
            className="text-muted py-4 text-center",
        )

    rows = []
    for item in plan:
        is_buy = item["action"] == "BUY"
        delta_pct = item["target_pct"] - Decimal(str(item["current_pct"]))
        rows.append(
            html.Tr(
                [
                    html.Td(html.Strong(item["ticker"])),
                    html.Td(item["name"]),
                    html.Td(_fmt_brl(item["current_value"])),
                    html.Td(f"{item['current_pct']:.2f}%"),
                    html.Td(f"{item['target_pct']:.2f}%"),
                    html.Td(
                        f"{delta_pct:+.2f}%",
                        className=("text-success fw-bold" if delta_pct > 0 else "text-muted"),
                    ),
                    html.Td(_fmt_brl(item["target_value"])),
                    html.Td(_fmt_brl(item["current_price"])),
                    html.Td(_fmt_brl(item["deficit"])),
                    html.Td(
                        html.Strong(str(item["recommended_buy_qty"]))
                        if is_buy
                        else html.Span("0", className="text-muted"),
                        className="text-success" if is_buy else "text-muted",
                    ),
                    html.Td(
                        html.Strong(_fmt_brl(item["estimated_cost"]))
                        if is_buy
                        else html.Span(_fmt_brl(0), className="text-muted"),
                        className="text-success fw-bold" if is_buy else "text-muted",
                    ),
                ]
            )
        )

    total_row = html.Tr(
        [
            html.Td(colSpan=9, className="text-end fw-bold"),
            html.Td(_fmt_brl(summary["total_estimated_cost"]), className="text-success fw-bold"),
            html.Td(
                f"Aporte: {_fmt_brl(summary['contribution'])} | "
                f"Sobra: {_fmt_brl(summary['leftover_amount'])}",
                className="text-muted small text-end",
            ),
        ]
    )

    return dbc.Table(
        [
            html.Thead(
                html.Tr(
                    [
                        html.Th("Ticker"),
                        html.Th("Ativo"),
                        html.Th("Valor Atual"),
                        html.Th("Atual (%)"),
                        html.Th("Alvo (%)"),
                        html.Th("Desvio"),
                        html.Th("Valor Alvo"),
                        html.Th("Cotação"),
                        html.Th("Déficit"),
                        html.Th("Comprar"),
                        html.Th("Custo"),
                    ]
                )
            ),
            html.Tbody(rows + [total_row]),
        ],
        bordered=True,
        hover=True,
        responsive=True,
        striped=True,
    )


@app.callback(
    Output("rebalance-estrategia-alerta", "children"),
    Output("rebalance-targets-container", "children"),
    Output("rebalance-plano-tabela", "children"),
    Input("auth-store", "data"),
    Input("store-reload-dashboard", "data"),
    Input("invest-tabs", "active_tab"),
    State("auth-store", "data"),
    prevent_initial_call=True,
)
def load_rebalance_tab(auth_data, _reload, _active_tab, auth_state):
    """Monta alerta de estratégia, editor de alvos e plano do aporte atual."""
    try:
        user_id = resolve_user(auth_state or auth_data)
    except AuthenticationError as e:
        return dbc.Alert(str(e), color="warning"), html.Div(), html.Div()

    try:
        with get_db_session() as db:
            overview = InvestmentRebalanceService(db).get_rebalance_overview(
                user_id,
                market_data_service=MarketDataService(db),
            )
    except Exception as e:  # noqa: BLE001
        app_logger.error(f"Erro ao carregar rebalanceamento: {e}")
        return (
            dbc.Alert("Não foi possível carregar a estratégia.", color="danger"),
            html.Div(),
            html.Div(),
        )

    return _strategy_alert(overview), _targets_editor(overview), html.Div()


@app.callback(
    Output("rebalance-plano-tabela", "children", allow_duplicate=True),
    Input("rebalance-aporte", "value"),
    State("auth-store", "data"),
    prevent_initial_call=True,
)
def recalc_rebalance_plan(aporte, auth_data):
    """Recalcula o plano a cada digitação do aporte (debounce do Input)."""
    try:
        user_id = resolve_user(auth_data)
    except AuthenticationError as e:
        return dbc.Alert(str(e), color="warning")

    try:
        amount = Decimal(str(aporte)) if aporte not in (None, "") else Decimal("0.00")
    except InvalidOperation:
        return dbc.Alert("Aporte inválido.", color="warning")
    try:
        with get_db_session() as db:
            rebalance = InvestmentRebalanceService(db)
            plan = rebalance.calculate_rebalance_plan(
                user_id,
                amount,
                market_data_service=MarketDataService(db),
            )
            summary = rebalance.get_plan_summary(plan, amount)
    except RebalanceValidationError as e:
        return dbc.Alert(str(e), color="warning")
    except Exception as e:  # noqa: BLE001
        app_logger.error(f"Erro ao calcular rebalanceamento: {e}")
        return dbc.Alert("Não foi possível calcular o plano.", color="danger")

    return _plan_table(plan, summary)


@app.callback(
    Output("rebalance-save-feedback", "children"),
    Input("rebalance-btn-salvar", "n_clicks"),
    State({"type": "rebalance-target", "asset_id": ALL}, "value"),
    State("auth-store", "data"),
    prevent_initial_call=True,
)
def save_rebalance_strategy(n_clicks, targets, auth_data):
    """Persiste os alvos um a um; a trava de <=100% vale a cada gravação."""
    if not n_clicks:
        return no_update

    allowed, retry_after = hit("invest.target", client_ip(), limit=60, window_seconds=60)
    if not allowed:
        return dbc.Alert(
            f"Taxa de requisições excedida. Tente novamente em {retry_after}s.",
            color="warning",
        )

    try:
        user_id = resolve_user(auth_data)
    except AuthenticationError as e:
        return dbc.Alert(str(e), color="warning")

    entries = list(targets or [])
    if not entries:
        return dbc.Alert("Nenhum alvo informado.", color="warning")

    saved: list[str] = []
    try:
        with get_db_session() as db:
            service = InvestmentService(db)
            for entry in entries:
                asset_id = entry["id"]["asset_id"]
                raw = entry.get("value")
                pct = Decimal(str(raw)) if raw not in (None, "") else Decimal("0")
                service.set_target_allocation(user_id, int(asset_id), pct)
                saved.append(str(asset_id))
            allocations = service.get_target_allocations(user_id)
    except InvestmentValidationError as e:
        return dbc.Alert(
            [html.I(className="bi bi-x-circle me-2"), str(e)],
            color="warning",
        )
    except Exception as e:  # noqa: BLE001
        app_logger.error(f"Erro ao salvar estratégia de rebalanceamento: {e}")
        return dbc.Alert("Erro ao salvar a estratégia.", color="danger")

    total = allocations["total_target_pct"]
    total_fmt = f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    color = "success" if allocations["is_complete"] else "warning"
    return dbc.Alert(
        [html.I(className="bi bi-check-circle me-2"), f"Estratégia salva. Metas: {total_fmt}%."],
        color=color,
    )
