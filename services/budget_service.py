"""Serviço de Orçamentos (Budgets)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from database.enums import TransactionStatus, TransactionType
from database.models.budget import Budget
from database.models.category import Category
from database.models.transaction import Transaction
from utils.money import to_money2

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class BudgetProgress:
    """Progresso de consumo de um orçamento."""

    category_id: int
    category_name: str
    category_icon: str
    amount_limit: Decimal
    spent: Decimal
    percentage: float
    status: str


class BudgetService:
    """Motor de limites de gasto por categoria e competência mensal."""

    def __init__(self, db_session: Session):
        self.db = db_session

    def set_budget(
        self,
        *,
        user_id: int,
        category_id: int,
        month: int,
        year: int,
        amount_limit,
    ) -> Budget:
        """Cria ou atualiza o limite de uma categoria no mês/ano informado."""
        value = to_money2(amount_limit, where="budget.set")
        if value <= ZERO:
            raise ValueError("Valor do orçamento deve ser maior que zero.")
        if not (1 <= int(month) <= 12):
            raise ValueError("Mês deve estar entre 1 e 12.")

        category = self._owned_category(user_id, category_id)

        budget = (
            self.db.query(Budget)
            .filter(
                Budget.user_id == user_id,
                Budget.category_id == category.id,
                Budget.month == int(month),
                Budget.year == int(year),
            )
            .first()
        )

        if budget:
            budget.amount_limit = value
        else:
            budget = Budget(
                user_id=user_id,
                category_id=category.id,
                month=int(month),
                year=int(year),
                amount_limit=value,
            )
            self.db.add(budget)

        try:
            self.db.commit()
            self.db.refresh(budget)
        except Exception:
            self.db.rollback()
            raise

        return budget

    def get_budget_progress(
        self,
        user_id: int,
        month: int,
        year: int,
    ) -> list[BudgetProgress]:
        """Retorna limite, gasto e percentual por categoria orçada.

        A soma dos gastos é resolvida no banco com `SUM + GROUP BY`,
        sem carregar transações em memória.
        """
        if not (1 <= int(month) <= 12):
            raise ValueError("Mês deve estar entre 1 e 12.")

        spent_subquery = (
            self.db.query(
                Transaction.category_id.label("category_id"),
                func.sum(Transaction.base_amount).label("spent"),
            )
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.status != TransactionStatus.CANCELLED,
                extract("month", Transaction.due_date) == int(month),
                extract("year", Transaction.due_date) == int(year),
            )
            .group_by(Transaction.category_id)
            .subquery()
        )

        rows = (
            self.db.query(
                Budget,
                Category,
                func.coalesce(spent_subquery.c.spent, ZERO).label("spent"),
            )
            .join(Category, Budget.category_id == Category.id)
            .outerjoin(
                spent_subquery,
                spent_subquery.c.category_id == Budget.category_id,
            )
            .filter(
                Budget.user_id == user_id,
                Budget.month == int(month),
                Budget.year == int(year),
            )
            .order_by(Category.name.asc())
            .all()
        )

        progress: list[BudgetProgress] = []
        for budget, category, spent in rows:
            limit = to_money2(budget.amount_limit, where="budget.progress.limit")
            spent_amount = to_money2(spent, where="budget.progress.spent")

            if limit > ZERO:
                percentage = float((spent_amount / limit) * Decimal("100"))
            else:
                percentage = 0.0

            if percentage > 90:
                status = "EXCEEDED"
            elif percentage >= 76:
                status = "WARNING"
            else:
                status = "OK"

            progress.append(
                BudgetProgress(
                    category_id=category.id,
                    category_name=category.name,
                    category_icon=category.icon or "📁",
                    amount_limit=limit,
                    spent=spent_amount,
                    percentage=percentage,
                    status=status,
                )
            )

        return progress

    def get_budgets_by_period(
        self,
        user_id: int,
        month: int,
        year: int,
    ) -> list[Budget]:
        """Retorna os orçamentos definidos para um mês/ano."""
        return (
            self.db.query(Budget)
            .filter(
                Budget.user_id == user_id,
                Budget.month == int(month),
                Budget.year == int(year),
            )
            .order_by(Budget.category_id.asc())
            .all()
        )

    def delete_budget(self, user_id: int, budget_id: int) -> bool:
        """Remove um orçamento do usuário."""
        budget = (
            self.db.query(Budget).filter(Budget.id == budget_id, Budget.user_id == user_id).first()
        )
        if not budget:
            return False
        try:
            self.db.delete(budget)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return True

    def copy_budgets_from_previous_month(
        self,
        user_id: int,
        target_month: int,
        target_year: int,
    ) -> int:
        """Copia os limites do mês anterior, ignorando categorias já orçadas."""
        if target_month == 1:
            source_month = 12
            source_year = target_year - 1
        else:
            source_month = target_month - 1
            source_year = target_year

        previous_budgets = self.get_budgets_by_period(user_id, source_month, source_year)
        existing = {
            budget.category_id
            for budget in self.get_budgets_by_period(user_id, target_month, target_year)
        }

        copied = 0
        for previous in previous_budgets:
            if previous.category_id in existing:
                continue
            self.set_budget(
                user_id=user_id,
                category_id=previous.category_id,
                month=target_month,
                year=target_year,
                amount_limit=previous.amount_limit,
            )
            copied += 1
        return copied

    def _owned_category(self, user_id: int, category_id: int) -> Category:
        category = (
            self.db.query(Category)
            .filter(
                Category.id == category_id,
                (Category.user_id == user_id) | (Category.is_system.is_(True)),
            )
            .first()
        )
        if not category:
            raise ValueError("Categoria não encontrada para este usuário.")
        return category
