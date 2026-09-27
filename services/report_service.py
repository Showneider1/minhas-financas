"""
Serviço de relatórios — P0 (ADR-002).

- Valor canônico: `base_amount` (Decimal). Sem `t.amount`.
- Nomes de categoria/conta com fallback (None-safe).
- TRANSFER excluído de receitas/despesas/saldos.
- Totais PAID consistentes com BalanceService (paid_date no período).
"""
from datetime import date
from decimal import Decimal
from typing import Dict, Any
from sqlalchemy.orm import Session

from database.models.category import TransactionType
from database.models.transaction import TransactionStatus
from database.repositories.transaction_repo import TransactionRepository
from schemas.transaction_schema import TransactionFilter
from services.balance_service import BalanceService
from utils.date_helpers import get_month_range, get_year_range
from utils.money import money_sum


class ReportService:
    """Geração de relatórios (somente leitura, com isolamento por usuário)."""

    def __init__(self, db: Session):
        self.db = db
        self.transaction_repo = TransactionRepository(db)
        self.balances = BalanceService(db)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _row(t) -> Dict[str, Any]:
        category = t.category.name if t.category else "Sem categoria"
        account = t.account.name if t.account else "Sem conta"
        return {
            "id": t.id,
            "data": t.due_date.isoformat(),
            "descricao": t.description,
            "categoria": category,
            "conta": account,
            "valor": str(t.base_amount),
            "tipo": t.transaction_type.value,
            "status": t.status.value,
        }

    def _totals(self, user_id: int, start_date: date, end_date: date):
        summary = self.balances.get_period_summary(user_id, start_date, end_date)
        return summary

    # ------------------------------------------------------------------
    # Relatórios
    # ------------------------------------------------------------------
    def generate_monthly_report(self, user_id: int, year: int, month: int) -> Dict[str, Any]:
        """Relatório mensal (totais PAID + categorias + lançamentos)."""
        start_date, end_date = get_month_range(year, month)

        transactions, total = self.transaction_repo.filter_transactions(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            page=1,
            page_size=10000,
        )

        categories_income = self.transaction_repo.get_category_totals(
            user_id, TransactionType.INCOME, start_date, end_date
        )
        categories_expense = self.transaction_repo.get_category_totals(
            user_id, TransactionType.EXPENSE, start_date, end_date
        )
        summary = self._totals(user_id, start_date, end_date)

        return {
            "periodo": {
                "mes": month,
                "ano": year,
                "inicio": start_date.isoformat(),
                "fim": end_date.isoformat(),
            },
            "resumo": {
                "total_receitas": str(summary["income_paid"]),
                "total_despesas": str(summary["expense_paid"]),
                "saldo": str(summary["balance_paid"]),
                "total_transacoes": total,
            },
            "categorias": {
                "receitas": categories_income,
                "despesas": categories_expense,
            },
            "transacoes": [self._row(t) for t in transactions],
        }

    def generate_annual_report(self, user_id: int, year: int) -> Dict[str, Any]:
        """Relatório anual (totais + evolução mensal + categorias)."""
        start_date, end_date = get_year_range(year)

        monthly_data = []
        for month in range(1, 13):
            month_start, month_end = get_month_range(year, month)
            summary = self._totals(user_id, month_start, month_end)
            monthly_data.append({
                "mes": month,
                "receitas": str(summary["income_paid"]),
                "despesas": str(summary["expense_paid"]),
                "saldo": str(summary["balance_paid"]),
            })

        annual = self._totals(user_id, start_date, end_date)
        categories_income = self.transaction_repo.get_category_totals(
            user_id, TransactionType.INCOME, start_date, end_date
        )
        categories_expense = self.transaction_repo.get_category_totals(
            user_id, TransactionType.EXPENSE, start_date, end_date
        )

        def _monthly_avg(total: Decimal) -> Decimal:
            return (total / 12).quantize(Decimal("0.01"))

        return {
            "ano": year,
            "resumo": {
                "total_receitas": str(annual["income_paid"]),
                "total_despesas": str(annual["expense_paid"]),
                "saldo": str(annual["balance_paid"]),
                "media_mensal_receitas": str(_monthly_avg(annual["income_paid"])),
                "media_mensal_despesas": str(_monthly_avg(annual["expense_paid"])),
            },
            "evolucao_mensal": monthly_data,
            "categorias": {
                "receitas": categories_income,
                "despesas": categories_expense,
            },
        }

    def generate_custom_report(
        self, user_id: int, filters: TransactionFilter
    ) -> Dict[str, Any]:
        """Relatório com filtros (usa apenas campos existentes do schema)."""
        transactions, total = self.transaction_repo.filter_transactions(
            user_id=user_id,
            start_date=filters.start_date,
            end_date=filters.end_date,
            transaction_type=filters.transaction_type,
            status=filters.status,
            category_ids=[filters.category_id] if filters.category_id else None,
            account_ids=[filters.account_id] if filters.account_id else None,
            page=1,
            page_size=10000,
        )

        # Totais SOMENTE do realizado PAID no conjunto (TRANSFER excluído).
        paid = [t for t in transactions if t.status == TransactionStatus.PAID]
        total_income = money_sum(
            t.base_amount for t in paid
            if t.transaction_type == TransactionType.INCOME
        )
        total_expense = money_sum(
            t.base_amount for t in paid
            if t.transaction_type == TransactionType.EXPENSE
        )

        return {
            "filtros": filters.model_dump(exclude_none=True),
            "resumo": {
                "total_transacoes": total,
                "total_receitas": str(total_income),
                "total_despesas": str(total_expense),
                "saldo": str(total_income - total_expense),
                # A lista inclui TRANSFER (visibilidade); totais só INCOME/EXPENSE.
                "inclui_transferencias": True,
            },
            "transacoes": [self._row(t) for t in transactions],
        }
