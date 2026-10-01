"""Registra todos os callbacks do Dash no app."""

from config.logging_config import app_logger

_CALLBACK_MODULES = [
    "callbacks.auth_callbacks",
    "callbacks.sidebar_callbacks",
    "callbacks.config_callbacks",
    "callbacks.dashboard_callbacks",
    "callbacks.extrato_callbacks",
    "callbacks.transactions_callbacks",
    "callbacks.account_callbacks",
    "callbacks.category_callbacks",
    "callbacks.export_callbacks",
    "callbacks.budget_callbacks",
    "callbacks.goal_callbacks",
    "callbacks.investimentos_callbacks",
    "callbacks.recorrencia_callbacks",
    "callbacks.cartoes_callbacks",
    "callbacks.analytics_callbacks",
    "callbacks.importacao_callbacks",
    "callbacks.relatorios_callbacks",
    "callbacks.dashboard_projection_callback",
]

for _module_name in _CALLBACK_MODULES:
    try:
        __import__(_module_name)
        app_logger.info(f"Callback registrado: {_module_name}")
    except Exception as _exc:  # noqa: BLE001
        app_logger.warning(f"Falha ao registrar callback {_module_name}: {_exc}")
