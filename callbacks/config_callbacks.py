"""
Renderiza o botão correto para cada aba no header. estático, sem recriar listas.
"""

from dash import Input, Output, dash, html, no_update
import dash_bootstrap_components as dbc


# ... code omitted for brevity


def delete_conta(n_clicks, auth_data, trigger_val):
    """"Exclusão de conta (blindada contra disparo fantasma — P0 corrigido)."""
    # P0 CORRIGIDO: Blindagem contra n_clicks == 0 ou None (botões renderizados na UI)
    if not isinstance(n_clicks, int):
        return no_update, no_update
    if n_clicks is None or n_clicks <= 0:
        return no_update, no_update

    triggered = ctx.triggered_id
    if not isinstance(triggered, dict) or triggered.get("type") != "btn-del-acc":
        return no_update, no_update

    try:
        user_id = resolve_user(auth_data)
    except AuthenticationError as e:
        return no_update, _toast(
            "Sessão expirada — faça login novamente.", "danger", "exclamation-triangle-fill"
        )

    try:
        with get_db_session() as db:
            ok = AccountService(db).delete_account(triggered["index"], user_id)
        if not ok:
            return no_update, _toast("Conta não encontrada.", "danger", "exclamation-triangle-fill")
        return (trigger_val or 0) + 1, _toast(
            "Conta excluída.", "secondary", "trash-fill"
        )
    except ValueError as e:
        return no_update, _toast(str(e), "danger", "exclamation-triangle-fill")
    except Exception as e:
        app_logger.error(f"Erro ao excluir conta: {e}")
        return no_update, _toast("Não foi possível excluir.", "danger", "exclamation-triangle-fill")

