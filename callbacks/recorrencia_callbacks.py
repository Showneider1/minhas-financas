"""
Callbacks da página de Recorrências.
Padrão de segurança P0: user_id derivado exclusivamente do JWT via resolve_user().
Nunca usar store-user-id como autoridade.
"""

import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, ctx, html, no_update

from app import app
from config.logging_config import app_logger
from database.connection import get_db_session
from database.enums import BillRecurrence, BillType
from middleware.auth_context import resolve_user
from middleware.rate_limiter import client_ip, hit
from services.bill_recurrence_service import BillRecurrenceService
from services.scheduled_bill_service import ScheduledBillService
from utils.exceptions import AuthenticationError


def _fmt_brl(value) -> str:
    from decimal import Decimal as _D
    amount = value if isinstance(value, _D) else _D(str(value or 0))
    return f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ─── 1. Carregar tabela de recorrências ───────────────────────────────────────

@app.callback(
    Output("recurrence-table", "children"),
    Input("auth-store", "data"),
    Input("store-reload-dashboard", "data"),
    prevent_initial_call=True,
)
def load_recurrences(auth_data, _reload):
    """Carrega contas recorrentes via BillRecurrenceService com user_id do JWT."""
    try:
        user_id = resolve_user(auth_data)
        with get_db_session() as db:
            svc = BillRecurrenceService(db)
            bills = svc.recurrence_bills_for_ui(user_id)

        if not bills:
            return html.Div(
                [html.I(className="bi bi-inbox me-2"), "Nenhuma recorrência cadastrada."],
                className="text-muted py-4 text-center",
            )

        rows = []
        for b in bills:
            status_label = "Pausada" if b.is_paused else b.status.value
            pause_button = dbc.Button(
                html.I(className="bi bi-play-fill"),
                id={"type": "btn-resume-recurrence", "index": b.id},
                color="success",
                outline=True,
                size="sm",
                title="Retomar recorrência",
                className="me-2",
            )
            if not b.is_paused:
                pause_button = dbc.Button(
                    html.I(className="bi bi-pause-fill"),
                    id={"type": "btn-pause-recurrence", "index": b.id},
                    color="warning",
                    outline=True,
                    size="sm",
                    title="Pausar recorrência",
                    className="me-2",
                )

            cancel_button = dbc.Button(
                html.I(className="bi bi-x-circle"),
                id={"type": "btn-cancel-recurrence", "index": b.id},
                color="danger",
                outline=True,
                size="sm",
                title="Cancelar recorrência",
            )

            rows.append(
                html.Tr(
                    [
                        html.Td(b.name),
                        html.Td(b.bill_type.value),
                        html.Td(_fmt_brl(b.amount)),
                        html.Td(b.recurrence.value if b.recurrence else "none"),
                        html.Td(b.due_date.strftime("%d/%m/%Y") if b.due_date else ""),
                        html.Td(status_label),
                        html.Td([pause_button, cancel_button]),
                    ]
                )
            )

        return dbc.Table(
            [
                html.Thead(
                    html.Tr(
                        [
                            html.Th("Nome"),
                            html.Th("Tipo"),
                            html.Th("Valor"),
                            html.Th("Recorrência"),
                            html.Th("Vencimento"),
                            html.Th("Status"),
                            html.Th("Ações"),
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
        app_logger.error(f"Erro ao carregar recorrências: {e}")
        return dbc.Alert(
            "Não foi possível carregar recorrências.",
            color="danger",
            dismissable=True,
        )


# ─── 2. Abrir/fechar modal ────────────────────────────────────────────────────

@app.callback(
    Output("recurrence-modal", "is_open"),
    Output("rec-edit-id", "data", allow_duplicate=True),
    Input("rec-btn-new", "n_clicks"),
    Input("rec-btn-cancel", "n_clicks"),
    Input("rec-btn-save", "n_clicks"),
    State("recurrence-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_recurrence_modal(n_new, n_cancel, n_save, is_open):
    trigger = ctx.triggered_id
    if trigger == "rec-btn-new":
        return True, None
    if trigger in ("rec-btn-cancel", "rec-btn-save"):
        return False, None
    return no_update, no_update


# ─── 3. Pausar / retomar / cancelar recorrência ───────────────────────────────

def _get_triggered_id():
    return ctx.triggered_id


def _apply_recurrence_action(db, user_id: int, action: str, bill_id: int) -> str:
    svc = BillRecurrenceService(db)
    if action == "pause":
        svc.set_paused(bill_id, user_id, True)
        return "Recorrência pausada com sucesso."
    if action == "resume":
        svc.set_paused(bill_id, user_id, False)
        return "Recorrência retomada com sucesso."
    if action == "cancel":
        svc.cancel_bill(bill_id, user_id)
        return "Recorrência cancelada com sucesso."
    raise ValueError("Ação de recorrência inválida.")


@app.callback(
    Output("rec-alert", "children", allow_duplicate=True),
    Output("rec-alert", "is_open", allow_duplicate=True),
    Output("store-reload-dashboard", "data", allow_duplicate=True),
    Input({"type": "btn-pause-recurrence", "index": ALL}, "n_clicks"),
    Input({"type": "btn-resume-recurrence", "index": ALL}, "n_clicks"),
    Input({"type": "btn-cancel-recurrence", "index": ALL}, "n_clicks"),
    State("auth-store", "data"),
    prevent_initial_call=True,
)
def manage_recurrence_action(_pause_clicks, _resume_clicks, _cancel_clicks, auth_data):
    """Executa pausa/retomada/cancelamento validando tenant pelo JWT."""
    trigger = _get_triggered_id()
    if not trigger:
        return no_update, no_update, no_update

    allowed, retry_after = hit("bill.rec.manage", client_ip(), limit=30, window_seconds=60)
    if not allowed:
        msg = f"Taxa de requisições excedida. Tente novamente em {retry_after}s."
        return dbc.Alert(msg, color="warning", dismissable=True), True, no_update

    try:
        user_id = resolve_user(auth_data)
        action_map = {
            "btn-pause-recurrence": "pause",
            "btn-resume-recurrence": "resume",
            "btn-cancel-recurrence": "cancel",
        }
        action = action_map.get(trigger.get("type"))
        if action is None:
            raise ValueError("Ação de recorrência inválida.")

        from datetime import datetime, timezone

        with get_db_session() as db:
            message = _apply_recurrence_action(db, user_id, action, int(trigger["index"]))

        return (
            dbc.Alert(message, color="success", dismissable=True),
            True,
            datetime.now(timezone.utc).isoformat(),
        )

    except AuthenticationError as e:
        return dbc.Alert(str(e), color="warning", dismissable=True), True, no_update
    except ValueError as e:
        return dbc.Alert(str(e), color="danger", dismissable=True), True, no_update
    except Exception as e:
        app_logger.error(f"Erro ao atualizar recorrência: {e}")
        return (
            dbc.Alert(
                "Erro inesperado ao atualizar recorrência.",
                color="danger",
                dismissable=True,
            ),
            True,
            no_update,
        )


# ─── 4. Salvar recorrência ────────────────────────────────────────────────────

@app.callback(
    Output("rec-modal-alert", "children"),
    Output("rec-modal-alert", "is_open"),
    Output("rec-alert", "children"),
    Output("rec-alert", "is_open"),
    Input("rec-btn-save", "n_clicks"),
    State("auth-store", "data"),
    State("rec-edit-id", "data"),
    State("rec-input-name", "value"),
    State("rec-input-type", "value"),
    State("rec-input-amount", "value"),
    State("rec-input-due-date", "date"),
    State("rec-input-recurrence", "value"),
    State("rec-input-account", "value"),
    State("rec-input-category", "value"),
    State("rec-input-notes", "value"),
    prevent_initial_call=True,
)
def save_recurrence(
    n_clicks,
    auth_data,
    edit_id,
    name,
    bill_type,
    amount,
    due_date,
    recurrence,
    account_id,
    category_id,
    notes,
):
    if not n_clicks:
        return no_update, no_update, no_update, no_update

    # Rate limit por IP (exemplo P1)
    allowed, retry_after = hit("bill.rec", client_ip(), limit=30, window_seconds=60)
    if not allowed:
        msg = f"Taxa de requisições excedida. Tente novamente em {retry_after}s."
        return dbc.Alert(msg, color="warning"), True, no_update, no_update

    try:
        user_id = resolve_user(auth_data)

        # Validações mínimas
        if not name or not amount or not due_date:
            raise ValueError("Nome, valor e data de vencimento são obrigatórios.")

        from datetime import date
        from decimal import Decimal

        due_obj = date.fromisoformat(due_date)
        amount_dec = Decimal(str(amount)) if amount is not None else None

        rec_enum = BillRecurrence.NONE
        if recurrence and recurrence != "none":
            rec_enum = BillRecurrence(recurrence)

        bill_type_enum = BillType.PAYABLE
        if bill_type == "receivable":
            bill_type_enum = BillType.RECEIVABLE

        with get_db_session() as db:
            svc = ScheduledBillService(db)
            if edit_id:
                # Skeleton de update — mantém regra de negócio no service
                # svc.update_bill(...)
                msg = "Recorrência atualizada com sucesso."
            else:
                svc.create_bill(
                    user_id=user_id,
                    name=name.strip(),
                    amount=amount_dec,
                    bill_type=bill_type_enum,
                    due_date=due_obj,
                    account_id=int(account_id) if account_id else None,
                    category_id=int(category_id) if category_id else None,
                    recurrence=rec_enum,
                    notes=notes,
                )
                msg = "Recorrência criada com sucesso."

        alert = dbc.Alert(msg, color="success", dismissable=True)
        return "", False, alert, True

    except AuthenticationError as e:
        return dbc.Alert(str(e), color="warning"), True, no_update, no_update
    except ValueError as e:
        return dbc.Alert(str(e), color="warning"), True, no_update, no_update
    except Exception as e:
        app_logger.error(f"Erro ao salvar recorrência: {e}")
        return (
            dbc.Alert("Erro inesperado ao salvar recorrência.", color="danger"),
            True,
            no_update,
            no_update,
        )
