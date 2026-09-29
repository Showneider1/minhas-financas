"""Serviço de Analytics — agregações otimizadas para relatórios visuais."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from dateutil.relativedelta import relativedelta
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from database.enums import TransactionStatus, TransactionType
from database.models.category import Category
from database.models.transaction import Transaction
from utils.money import to_money2


class AnalyticsService:
    """Agregações analíticas prontas para Plotly/Dash.

    Todas as somas e agrupamentos são delegados ao banco via SQLAlchemy,
    evitando carregar transações em memória.
    """

    def __init__(self, db: Session):
        self.db = db

    def _validate_period(self, month: int, year: int) -> None:
        if not (1 <= int(month) <= 12):
            raise ValueError("Mês deve estar entre 1 e 12.")
        if int(year) < 2000:
            raise ValueError("Ano inválido.")

    @staticmethod
    def _reference_date():
        """Data de competência: usa pagamento quando existir, senão vencimento."""
        return func.coalesce(Transaction.paid_date, Transaction.due_date)

    def get_expenses_by_category(
        self,
        user_id: int,
        month: int,
        year: int,
    ) -> list[dict[str, Any]]:
        """Despesas agrupadas por categoria no mês/ano selecionado.

        - Ignora TRANSFER por construção (filtra apenas EXPENSE).
        - Ignora CANCELLED.
        - Agrupa no banco com SUM + GROUP BY.
        """
        self._validate_period(month, year)

        reference_date = self._reference_date()
        year_expr = func.extract("year", reference_date)
        month_expr = func.extract("month", reference_date)

        rows = (
            self.db.query(
                Category.name,
                Category.icon,
                Category.color,
                func.sum(Transaction.base_amount).label("total"),
            )
            .join(Transaction, Transaction.category_id == Category.id)
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.status != TransactionStatus.CANCELLED,
                year_expr == int(year),
                month_expr == int(month),
            )
            .group_by(
                Category.name,
                Category.icon,
                Category.color,
            )
            .order_by(func.sum(Transaction.base_amount).desc())
            .all()
        )

        return [
            {
                "name": row.name,
                "icon": row.icon or "📁",
                "color": row.color or "#95a5a6",
                "total": to_money2(row.total or 0, where="analytics.category.total"),
            }
            for row in rows
        ]

    def get_cash_flow_history(
        self,
        user_id: int,
        limit_months: int = 6,
    ) -> list[dict[str, Any]]:
        """Receitas vs Despesas dos últimos N meses.

        - Usa a data de competência: `paid_date` ou `due_date`.
        - Exclui TRANSFER e CANCELLED.
        - Agrega no banco com SUM condicional + GROUP BY.
        - Meses sem movimentação são preenchidos com zero.
        """
        if limit_months < 1:
            raise ValueError("O histórico deve conter pelo menos 1 mês.")
        if limit_months > 60:
            raise ValueError("O histórico não pode exceder 60 meses.")

        today = date.today()
        current_month = today.replace(day=1)
        months = [
            current_month - relativedelta(months=index) for index in range(limit_months - 1, -1, -1)
        ]
        start_date = months[0]
        end_date = months[-1] + relativedelta(months=1) - relativedelta(days=1)

        reference_date = self._reference_date()
        year_expr = func.extract("year", reference_date).label("year")
        month_expr = func.extract("month", reference_date).label("month")

        income_sum = func.sum(
            case(
                (
                    Transaction.transaction_type == TransactionType.INCOME,
                    Transaction.base_amount,
                ),
                else_=Decimal("0"),
            )
        ).label("income")

        expense_sum = func.sum(
            case(
                (
                    Transaction.transaction_type == TransactionType.EXPENSE,
                    Transaction.base_amount,
                ),
                else_=Decimal("0"),
            )
        ).label("expense")

        rows = (
            self.db.query(
                year_expr,
                month_expr,
                income_sum,
                expense_sum,
            )
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type.in_([TransactionType.INCOME, TransactionType.EXPENSE]),
                Transaction.status != TransactionStatus.CANCELLED,
                reference_date >= start_date,
                reference_date <= end_date,
            )
            .group_by(year_expr, month_expr)
            .all()
        )

        results_by_period = {
            (int(row.year), int(row.month)): (
                to_money2(row.income or 0, where="analytics.cashflow.income"),
                to_money2(row.expense or 0, where="analytics.cashflow.expense"),
            )
            for row in rows
        }

        history: list[dict[str, Any]] = []
        for month_start in months:
            key = (month_start.year, month_start.month)
            income, expense = results_by_period.get(key, (Decimal("0.00"), Decimal("0.00")))
            history.append(
                {
                    "label": month_start.strftime("%b/%Y"),
                    "year": month_start.year,
                    "month": month_start.month,
                    "income": income,
                    "expenses": expense,
                    "net": to_money2(income - expense, where="analytics.cashflow.net"),
                }
            )

        return history
