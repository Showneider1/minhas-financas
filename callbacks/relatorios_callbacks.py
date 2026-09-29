"""Callbacks de exportação de relatórios."""

from dash import Input, Output, State, dcc, no_update

from app import app
from config.logging_config import app_logger
from database.connection import get_db_session
from middleware.auth_context import resolve_user
from services.report_service import ReportService
from utils.exceptions import AuthenticationError


@app.callback(
    Output("download-report", "data"),
    Input("btn-gerar-relatorio", "n_clicks"),
    State("auth-store", "data"),
    State("relatorio-mes", "value"),
    State("relatorio-ano", "value"),
    State("relatorio-tipo", "value"),
    State("relatorio-formato", "value"),
    prevent_initial_call=True,
)
def generate_report(
    n_clicks,
    auth_data,
    month,
    year,
    report_type,
    report_format,
):
    """Gera e envia o relatório selecionado."""
    if not n_clicks:
        return no_update

    try:
        user_id = resolve_user(auth_data)
        with get_db_session() as db:
            service = ReportService(db)
            if report_type == "budget":
                dataframe = service.generate_budget_closing(
                    user_id,
                    int(month),
                    int(year),
                )
                base_name = f"fechamento-orcamentario-{year}-{int(month):02d}"
            else:
                dataframe = service.generate_monthly_extract(
                    user_id,
                    int(month),
                    int(year),
                )
                base_name = f"extrato-mensal-{year}-{int(month):02d}"

        if report_format == "xlsx":
            return dcc.send_data_frame(
                dataframe.to_excel,
                filename=f"{base_name}.xlsx",
                index=False,
                sheet_name="Relatório",
            )

        return dcc.send_data_frame(
            dataframe.to_csv,
            filename=f"{base_name}.csv",
            index=False,
            sep=";",
            encoding="utf-8-sig",
        )

    except AuthenticationError as exc:
        app_logger.warning(f"Exportação bloqueada: {exc}")
        return no_update
    except Exception as exc:
        app_logger.error(f"Erro ao gerar relatório: {exc}")
        return no_update
