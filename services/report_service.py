"""
Serviço de relatórios — P0 (ADR-002).

- Valor canônico: `base_amount` (Decimal). Sem `t.amount`.
- Nomes de categoria/conta com fallback (None-safe).
- TRANSFER excluído de receitas/despesas/saldos.
- Totais PAID consistentes com BalanceService (paid_date no período).
"""

from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd
from sqlalchemy import extract
from sqlalchemy.orm import Session

from database.models.account import Account
from database.models.category import Category, TransactionType
from database.models.transaction import Transaction, TransactionStatus
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
    # Exportação mensal
    # ------------------------------------------------------------------
    def generate_monthly_extract(self, user_id: int, month: int, year: int) -> pd.DataFrame:
        """Extrai o consolidado mensal em DataFrame pronto para exportação.

        - Isolamento estrito por `user_id`
        - Filtra competência por `due_date`
        - Exclui apenas transações canceladas
        - Preserva valores com `Decimal` até a borda de serialização
        """
        if not (1 <= int(month) <= 12):
            raise ValueError("Mês deve estar entre 1 e 12.")

        rows = (
            self.db.query(
                Transaction,
                Category.name.label("category_name"),
                Category.icon.label("category_icon"),
                Account.name.label("account_name"),
            )
            .join(Category, Transaction.category_id == Category.id)
            .join(Account, Transaction.account_id == Account.id)
            .filter(
                Transaction.user_id == user_id,
                Transaction.status != TransactionStatus.CANCELLED,
                extract("month", Transaction.due_date) == int(month),
                extract("year", Transaction.due_date) == int(year),
            )
            .order_by(Transaction.due_date.asc(), Transaction.id.asc())
            .all()
        )

        records = []
        for transaction, category_name, category_icon, account_name in rows:
            category_label = f"{category_icon or ''} {category_name or 'Sem categoria'}".strip()
            records.append(
                {
                    "Data": transaction.due_date.strftime("%d/%m/%Y"),
                    "Descrição": transaction.description,
                    "Categoria": category_label,
                    "Tipo": self._transaction_type_label(transaction.transaction_type),
                    "Conta Origem": account_name or "Sem conta",
                    "Valor": f"{transaction.base_amount:.2f}".replace(".", ","),
                    "Status": self._status_label(transaction.status),
                }
            )

        return pd.DataFrame(
            records,
            columns=[
                "Data",
                "Descrição",
                "Categoria",
                "Tipo",
                "Conta Origem",
                "Valor",
                "Status",
            ],
        )

    def generate_budget_closing(self, user_id: int, month: int, year: int) -> pd.DataFrame:
        """Extrai o fechamento orçamentário do mês em DataFrame."""
        if not (1 <= int(month) <= 12):
            raise ValueError("Mês deve estar entre 1 e 12.")

        from services.budget_service import BudgetService

        progress = BudgetService(self.db).get_budget_progress(user_id, month, year)
        records = [
            {
                "Categoria": f"{item.category_icon} {item.category_name}".strip(),
                "Limite": f"{item.amount_limit:.2f}".replace(".", ","),
                "Gasto": f"{item.spent:.2f}".replace(".", ","),
                "% Usado": f"{item.percentage:.1f}".replace(".", ","),
                "Status": item.status,
            }
            for item in progress
        ]

        return pd.DataFrame(
            records,
            columns=["Categoria", "Limite", "Gasto", "% Usado", "Status"],
        )

    @staticmethod
    def _transaction_type_label(transaction_type) -> str:
        return {
            TransactionType.INCOME: "Receita",
            TransactionType.EXPENSE: "Despesa",
            TransactionType.TRANSFER: "Transferência",
        }.get(transaction_type, "Outro")

    @staticmethod
    def _status_label(status) -> str:
        return {
            TransactionStatus.PAID: "Pago",
            TransactionStatus.PENDING: "Pendente",
            TransactionStatus.CANCELLED: "Cancelado",
        }.get(status, "Outro")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _row(t) -> dict[str, Any]:
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
    def generate_monthly_report(self, user_id: int, year: int, month: int) -> dict[str, Any]:
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

    def generate_annual_report(self, user_id: int, year: int) -> dict[str, Any]:
        """Relatório anual (totais + evolução mensal + categorias)."""
        start_date, end_date = get_year_range(year)

        monthly_data = []
        for month in range(1, 13):
            month_start, month_end = get_month_range(year, month)
            summary = self._totals(user_id, month_start, month_end)
            monthly_data.append(
                {
                    "mes": month,
                    "receitas": str(summary["income_paid"]),
                    "despesas": str(summary["expense_paid"]),
                    "saldo": str(summary["balance_paid"]),
                }
            )

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

    def generate_custom_report(self, user_id: int, filters: TransactionFilter) -> dict[str, Any]:
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
            t.base_amount for t in paid if t.transaction_type == TransactionType.INCOME
        )
        total_expense = money_sum(
            t.base_amount for t in paid if t.transaction_type == TransactionType.EXPENSE
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
