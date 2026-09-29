"""Callbacks da página de Importação Bancária."""

import base64
from decimal import Decimal

import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, html, no_update

from app import app
from config.logging_config import app_logger
from database.connection import get_db_session
from database.enums import AccountType
from database.models.category import Category
from middleware.auth_context import resolve_user
from services.account_service import AccountService
from services.import_service import (
    DUPLICATE_FOUND,
    ImportService,
)
from utils.exceptions import AuthenticationError


def _fmt_brl(value) -> str:
    amount = value if isinstance(value, Decimal) else Decimal(str(value or 0))
    return f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _alert(message: str, color: str = "danger") -> dbc.Alert:
    return dbc.Alert(message, color=color, dismissable=True, className="mb-0")


@app.callback(
    Output("import-account", "options"),
    Input("url", "pathname"),
    Input("auth-store", "data"),
    prevent_initial_call=True,
)
def load_import_accounts(pathname, auth_data):
    """Carrega contas não-cartão disponíveis para importação."""
    if pathname != "/importacao":
        return no_update
    if not auth_data:
        return []

    try:
        user_id = resolve_user(auth_data)
    except AuthenticationError:
        return []

    try:
        with get_db_session() as db:
            accounts = [
                account
                for account in AccountService(db).get_user_accounts(user_id)
                if account.account_type != AccountType.CREDIT_CARD
            ]
            return [{"label": account.name, "value": account.id} for account in accounts]
    except Exception as exc:
        app_logger.error(f"Erro ao carregar contas para importação: {exc}")
        return []


@app.callback(
    Output("import-preview-store", "data"),
    Output("import-preview-container", "children"),
    Output("import-file-info", "children"),
    Output("import-feedback", "children"),
    Output("import-feedback", "is_open"),
    Input("import-upload", "contents"),
    State("import-upload", "filename"),
    State("import-account", "value"),
    State("auth-store", "data"),
    prevent_initial_call=True,
)
def preview_import(
    contents,
    filename,
    account_id,
    auth_data,
):
    """Recebe o arquivo, faz o parse e exibe a pré-visualização."""
    if not contents:
        return no_update, no_update, no_update, no_update, no_update
    if not account_id:
        return (
            no_update,
            no_update,
            no_update,
            _alert("Selecione a conta de destino antes de importar.", "warning"),
            True,
        )

    try:
        user_id = resolve_user(auth_data)
        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)

        with get_db_session() as db:
            service = ImportService(db)
            rows = service.parse_file(
                decoded,
                filename=filename,
                account_id=int(account_id),
                user_id=user_id,
            )
            categories_by_type = _load_categories_by_type(db, user_id)

        table = _build_preview_table(rows, categories_by_type)
        info = f"Arquivo carregado: {filename} — {len(rows)} transação(ões) detectada(s)."

        return rows, table, info, "", False

    except AuthenticationError as exc:
        return (
            no_update,
            no_update,
            no_update,
            _alert(str(exc), "warning"),
            True,
        )
    except Exception as exc:
        app_logger.error(f"Erro ao pré-visualizar importação: {exc}")
        return (
            no_update,
            no_update,
            no_update,
            _alert(f"Não foi possível ler o arquivo: {exc}", "danger"),
            True,
        )


@app.callback(
    Output("import-feedback", "children", allow_duplicate=True),
    Output("import-feedback", "is_open", allow_duplicate=True),
    Output("import-preview-store", "data", allow_duplicate=True),
    Output("import-preview-container", "children", allow_duplicate=True),
    Output("store-reload-dashboard", "data", allow_duplicate=True),
    Input("btn-process-import", "n_clicks"),
    State("import-account", "value"),
    State("import-preview-store", "data"),
    State({"type": "import-category", "index": ALL}, "value"),
    State("auth-store", "data"),
    State("store-reload-dashboard", "data"),
    prevent_initial_call=True,
)
def process_import(
    n_clicks,
    account_id,
    rows,
    category_ids,
    auth_data,
    reload_counter,
):
    """Importa as linhas selecionadas e atualiza os painéis."""
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update
    if not account_id:
        return (
            _alert("Selecione a conta de destino.", "warning"),
            True,
            no_update,
            no_update,
            no_update,
        )
    if not rows:
        return (
            _alert("Nenhum arquivo carregado para importar.", "warning"),
            True,
            no_update,
            no_update,
            no_update,
        )

    try:
        user_id = resolve_user(auth_data)

        with get_db_session() as db:
            service = ImportService(db)
            result = service.process_import(
                rows,
                category_ids=category_ids,
                account_id=int(account_id),
                user_id=user_id,
            )

        message = (
            f"Importação concluída: {result['imported']} nova(s), "
            f"{result['skipped']} duplicada(s), "
            f"{len(result['errors'])} erro(s)."
        )
        if result["errors"]:
            color = "warning"
        else:
            color = "success"

        return (
            _alert(message, color),
            True,
            [],
            html.Div(),
            (reload_counter or 0) + 1,
        )

    except AuthenticationError as exc:
        return (
            _alert(str(exc), "warning"),
            True,
            no_update,
            no_update,
            no_update,
        )
    except Exception as exc:
        app_logger.error(f"Erro ao processar importação: {exc}")
        return (
            _alert("Não foi possível processar a importação.", "danger"),
            True,
            no_update,
            no_update,
            no_update,
        )


def _load_categories_by_type(db, user_id: int) -> dict[str, list[dict]]:
    categories = (
        db.query(Category)
        .filter(
            (Category.user_id == user_id) | (Category.is_system.is_(True)),
            Category.transaction_type.isnot(None),
        )
        .order_by(Category.name.asc())
        .all()
    )

    result: dict[str, list[dict]] = {
        "INCOME": [],
        "EXPENSE": [],
    }
    for category in categories:
        if category.transaction_type.value not in result:
            continue
        result[category.transaction_type.value].append(
            {
                "label": f"{category.icon} {category.name}",
                "value": category.id,
            }
        )
    return result


def _build_preview_table(
    rows: list[dict],
    categories_by_type: dict[str, list[dict]],
) -> html.Div:
    if not rows:
        return html.Div("Nenhuma transação encontrada.", className="text-muted")

    header = html.Tr(
        [
            html.Th("Data"),
            html.Th("Descrição"),
            html.Th("Valor"),
            html.Th("Tipo"),
            html.Th("Status"),
            html.Th("Categoria"),
        ]
    )

    body_rows = []
    for row in rows:
        duplicate = row["status"] == DUPLICATE_FOUND
        row_class = "table-warning" if duplicate else ""
        status_color = "warning" if duplicate else "success"
        status_text = "Duplicada" if duplicate else "Nova"
        amount = Decimal(row["amount"])
        value_class = (
            "text-success fw-bold" if row["transaction_type"] == "INCOME" else "text-danger fw-bold"
        )

        options = categories_by_type.get(row["transaction_type"], [])
        selected = row.get("suggested_category_id")

        body_rows.append(
            html.Tr(
                [
                    html.Td(row["date"]),
                    html.Td(row["description"]),
                    html.Td(_fmt_brl(amount), className=f"text-end {value_class}"),
                    html.Td("Receita" if row["transaction_type"] == "INCOME" else "Despesa"),
                    html.Td(
                        dbc.Badge(
                            status_text,
                            color=status_color,
                            pill=True,
                        )
                    ),
                    html.Td(
                        dbc.Select(
                            id={"type": "import-category", "index": row["index"]},
                            options=options,
                            value=selected,
                            disabled=duplicate,
                            size="sm",
                        )
                    ),
                ],
                className=row_class,
            )
        )

    table = dbc.Table(
        [
            html.Thead(header),
            html.Tbody(body_rows),
        ],
        bordered=True,
        hover=True,
        responsive=True,
        striped=True,
        className="align-middle",
    )

    return html.Div(
        [
            html.Div(
                [
                    html.Small(
                        "Linhas amarelas já existem no sistema e serão ignoradas.",
                        className="text-muted d-block mb-2",
                    )
                ]
            ),
            table,
        ]
    )
