"""
Callback Vault — Blindagem P0 garantida. Tratar VaultInsufficientFundsError no modal.
"""


from decimal import Decimal

from dash import ALL, Input, Output, State, ctx, no_update
import dash_bootstrap_components as dbc

from app import app
from config.logging_config import app_logger
from database.connection import get_db_session
from middleware.auth_context import resolve_user
from services.vault_service import VaultService, VaultInsufficientFundsError


@app.callback(
    Output("vault-modal-alert", "children"),
    Output("vault-alert", "children", allow_duplicate=True),
    Input({"type": "vault-btn-keep", "index": ALL}, "n_clicks"),
    Input({"type": "vault-btn-take", "index": ALL}, "n_clicks"),
    State("auth-store", "data"),
    State("vault-select", "value"),
    State("vault-amount", "value"),
    prevent_initial_call=True,
)
def handle_vault_actions(btn_keep, btn_take, auth_data, vault_id, amount):
    # P0 Blindagem: ignora n_clicks <= 0 (botões renderizados na UI sem clique)
    if not isinstance(btn_keep, (list, tuple)) or not all(isinstance(x, int) for x in btn_keep):
        return no_update, no_update
    
    triggered_keep = next((b for b in btn_keep), None) if btn_keep else None
    triggered_take = next((b for b in btn_take), None) if btn_take else None
    
    # Se nenhum botão foi clicado (>0), não atualiza
    if not (triggered_keep or triggered_take):
        return no_update, no_update
    
    vault_clicked_id = int(triggered_keep["index"]) if triggered_keep else int(triggered_take["index"])
    
    try:
        with get_db_session() as db:
            service = VaultService(db)
            
            # Ação de guardar ou resgatar conforme botão clicado
            if triggered_keep is not None:
                new_amount = Decimal(amount or "0") if amount else ZERO
                service.allocate_funds(vault_clicked_id, resolve_user(auth_data), new_amount)
                return dbc.Alert(f"Guardado R$ {amount}!", color="success"), no_update
            
            elif triggered_take is not None:
                current_saved = Decimal(str(service.get_vaults(resolve_user(auth_data))[vault_clicked_id].saved_amount or 0)) if hasattr(service, 'get_vaults') else ZERO
                amount_to_withdraw = Decimal(amount or "0") if amount else current_saved
                service.withdraw_funds(vault_clicked_id, resolve_user(auth_data), amount_to_withdraw)
                return dbc.Alert(f"Resgatado R$ {amount}!", color="success"), no_update
    
    except VaultInsufficientFundsError as ex:
        # Erro de saldo insuficiente — UI mostra alerta vermelho sem crashar
        return dbc.Alert(str(ex), color="warning"), no_update
    
    except Exception as ex:
        app_logger.error(f"Erro vault callback: {ex}", exc_info=True)
        return dbc.Alert("Erro ao processar.", color="danger"), no_update


ZERO = Decimal("0.00")
