"""
Callbacks para exportação de dados.
"""

import io
from datetime import date, datetime

from dash import Input, Output, State, dcc
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func

from app import app
from config.logging_config import app_logger
from database.connection import get_db_session
from middleware.auth_context import resolve_user
from utils.exceptions import AuthenticationError


@app.callback(
    Output("download-extrato", "data"),
    Input("btn-export-pdf", "n_clicks"),
    State("auth-store", "data"),
    State("extrato-periodo", "start_date"),
    State("extrato-periodo", "end_date"),
    State("extrato-tipo", "value"),
    State("extrato-status", "value"),
    prevent_initial_call=True,
)
def exportar_extrato(n_clicks, auth_data, start_date, end_date, tipos, status_list):
    """
    Exporta extrato em PDF.
    """
    try:
        if not n_clicks or not auth_data:
            return None
        # P0 (IDOR): usuário derivado do JWT.
        user_id = resolve_user(auth_data)

        # Converte datas
        if start_date:
            data_inicio = datetime.fromisoformat(start_date).date()
        else:
            data_inicio = date.today().replace(day=1)

        if end_date:
            data_fim = datetime.fromisoformat(end_date).date()
        else:
            data_fim = date.today()

        with get_db_session() as db:
            from database.models.category import TransactionType
            from database.models.transaction import Transaction, TransactionStatus

            # Query (CANCELLED fora; tipos convertidos de string p/ enum)
            query = db.query(Transaction).filter(
                Transaction.user_id == user_id,
                Transaction.status != TransactionStatus.CANCELLED,
                Transaction.due_date >= data_inicio,
                Transaction.due_date <= data_fim,
            )

            # Filtros
            if tipos:
                wanted = []
                for raw in tipos:
                    try:
                        wanted.append(TransactionType(raw))
                    except ValueError:
                        continue
                if wanted:
                    query = query.filter(Transaction.transaction_type.in_(wanted))

            if status_list:
                if "PAID" in status_list and "PENDING" not in status_list:
                    query = query.filter(Transaction.paid_date.isnot(None))
                elif "PENDING" in status_list and "PAID" not in status_list:
                    query = query.filter(Transaction.paid_date.is_(None))

            query = query.order_by(Transaction.due_date.desc())
            transactions = query.all()

            # Gera PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()

            # Título
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=24,
                textColor=colors.HexColor("#2c3e50"),
                spaceAfter=30,
                alignment=TA_CENTER,
            )
            elements.append(Paragraph("Extrato Financeiro", title_style))
            elements.append(
                Paragraph(
                    (
                        f"Período: {data_inicio.strftime('%d/%m/%Y')} a "
                        f"{data_fim.strftime('%d/%m/%Y')}"
                    ),
                    styles["Normal"],
                )
            )
            elements.append(Spacer(1, 20))

            # Tabela
            data = [["Data", "Descrição", "Categoria", "Tipo", "Valor", "Status"]]

            for t in transactions:
                if t.transaction_type == TransactionType.INCOME:
                    tipo_str = "Receita"
                elif t.transaction_type == TransactionType.EXPENSE:
                    tipo_str = "Despesa"
                else:
                    tipo_str = "Transferência"
                status_str = "Pago" if t.paid_date else "Pendente"
                valor_str = _fmt_brl(t.base_amount)
                data_str = t.due_date.strftime("%d/%m/%Y")
                cat_name = t.category.name if t.category else "Sem categoria"

                data.append(
                    [data_str, t.description[:30], cat_name[:20], tipo_str, valor_str, status_str]
                )

            table = Table(
                data, colWidths=[1 * inch, 2 * inch, 1.5 * inch, 1 * inch, 1.2 * inch, 1 * inch]
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 12),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )

            elements.append(table)
            doc.build(elements)

            buffer.seek(0)
            filename = f"extrato_{data_inicio}_{data_fim}.pdf"

            return dcc.send_bytes(buffer.getvalue(), filename=filename)

    except AuthenticationError:
        return None
    except Exception as e:
        app_logger.error(f"Erro ao exportar: {e}")
        return None


def _fmt_brl(value) -> str:
    # Borda de exibição (sem aritmética aqui).
    from decimal import Decimal as _D

    amount = value if isinstance(value, _D) else _D(str(value or 0))
    return f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@app.callback(
    Output("download-dashboard", "data"),
    Input("btn-export-dashboard", "n_clicks"),
    State("auth-store", "data"),
    State("dashboard-periodo", "start_date"),
    State("dashboard-periodo", "end_date"),
    prevent_initial_call=True,
)
def exportar_dashboard(n_clicks, auth_data, start_date, end_date):
    """
    Exporta relatório do dashboard em PDF.
    """
    try:
        if not n_clicks or not auth_data:
            return None
        # P0 (IDOR): usuário derivado do JWT.
        user_id = resolve_user(auth_data)

        # Converte datas
        if start_date:
            data_inicio = datetime.fromisoformat(start_date).date()
        else:
            data_inicio = date.today().replace(day=1)

        if end_date:
            data_fim = datetime.fromisoformat(end_date).date()
        else:
            data_fim = date.today()

        with get_db_session() as db:
            from database.models.category import TransactionType
            from database.models.transaction import Transaction, TransactionStatus

            # Totais PAID (canônico: base_amount + status sincronizado)
            receitas = (
                db.query(func.sum(Transaction.base_amount))
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.transaction_type == TransactionType.INCOME,
                    Transaction.status == TransactionStatus.PAID,
                    Transaction.paid_date.isnot(None),
                    Transaction.paid_date >= data_inicio,
                    Transaction.paid_date <= data_fim,
                )
                .scalar()
                or 0
            )

            despesas = (
                db.query(func.sum(Transaction.base_amount))
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.transaction_type == TransactionType.EXPENSE,
                    Transaction.status == TransactionStatus.PAID,
                    Transaction.paid_date.isnot(None),
                    Transaction.paid_date >= data_inicio,
                    Transaction.paid_date <= data_fim,
                )
                .scalar()
                or 0
            )

            saldo = receitas - despesas

            # Gera PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()

            # Título
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=24,
                textColor=colors.HexColor("#2c3e50"),
                spaceAfter=30,
                alignment=TA_CENTER,
            )
            elements.append(Paragraph("Relatório Financeiro", title_style))
            elements.append(
                Paragraph(
                    (
                        f"Período: {data_inicio.strftime('%d/%m/%Y')} a "
                        f"{data_fim.strftime('%d/%m/%Y')}"
                    ),
                    styles["Normal"],
                )
            )
            elements.append(Spacer(1, 20))

            # Resumo
            data = [
                ["Métrica", "Valor"],
                ["Receitas", _fmt_brl(receitas)],
                ["Despesas", _fmt_brl(despesas)],
                ["Saldo", _fmt_brl(saldo)],
            ]

            table = Table(data, colWidths=[3 * inch, 3 * inch])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 14),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )

            elements.append(table)
            doc.build(elements)

            buffer.seek(0)
            filename = f"dashboard_{data_inicio}_{data_fim}.pdf"

            return dcc.send_bytes(buffer.getvalue(), filename=filename)

    except AuthenticationError:
        return None
    except Exception as e:
        app_logger.error(f"Erro ao exportar dashboard: {e}")
        return None
