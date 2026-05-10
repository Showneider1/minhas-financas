from sqlalchemy.orm import Session
from sqlalchemy import and_, func, extract
from database.models.budget import Budget
from database.models.transaction import Transaction, TransactionStatus
from database.models.category import TransactionType
from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class BudgetAlert:
    """
    Alerta de estouro ou aproximação do limite de orçamento de uma categoria.

    status:
        'OK'       — gasto < 80% do orçamento
        'WARNING'  — gasto entre 80% e 99% do orçamento
        'EXCEEDED' — gasto >= 100% do orçamento
    """
    category_id:   int
    category_name: str
    budget_amount: float
    spent_amount:  float
    pct_used:      float   # 0.0 – 100.0+
    status:        str     # 'OK' | 'WARNING' | 'EXCEEDED'


class BudgetService:
    def __init__(self, db_session: Session):
        self.db = db_session

    # ------------------------------------------------------------------
    # Métodos originais inalterados
    # ------------------------------------------------------------------

    def save_budget(self, user_id: int, category_id: int, amount: float, month: int, year: int) -> Budget:
        """
        Cria ou Atualiza (Upsert) uma meta.
        Se já existe meta para aquela categoria naquele mês, apenas atualiza o valor.
        """
        existing_budget = self.db.query(Budget).filter(
            Budget.user_id == user_id,
            Budget.category_id == category_id,
            Budget.month == month,
            Budget.year == year
        ).first()

        if existing_budget:
            existing_budget.amount = amount
            result = existing_budget
        else:
            new_budget = Budget(
                user_id=user_id,
                category_id=category_id,
                amount=amount,
                month=month,
                year=year
            )
            self.db.add(new_budget)
            result = new_budget

        self.db.commit()
        self.db.refresh(result)
        return result

    def get_budgets_by_period(self, user_id: int, month: int, year: int) -> List[Budget]:
        """Retorna todas as metas definidas para um mês/ano específico."""
        return self.db.query(Budget).filter(
            Budget.user_id == user_id,
            Budget.month == month,
            Budget.year == year
        ).all()

    def get_budget_by_category(self, user_id: int, category_id: int, month: int, year: int) -> Optional[Budget]:
        """Retorna uma meta específica de uma categoria."""
        return self.db.query(Budget).filter(
            Budget.user_id == user_id,
            Budget.category_id == category_id,
            Budget.month == month,
            Budget.year == year
        ).first()

    def delete_budget(self, user_id: int, budget_id: int) -> bool:
        """Remove uma meta."""
        budget = self.db.query(Budget).filter(
            Budget.id == budget_id,
            Budget.user_id == user_id
        ).first()

        if budget:
            self.db.delete(budget)
            self.db.commit()
            return True
        return False

    def copy_budgets_from_previous_month(self, user_id: int, target_month: int, target_year: int) -> int:
        """
        Copia todas as metas do mês anterior para o mês atual.
        Retorna o número de metas copiadas.
        """
        if target_month == 1:
            source_month = 12
            source_year = target_year - 1
        else:
            source_month = target_month - 1
            source_year = target_year

        previous_budgets = self.get_budgets_by_period(user_id, source_month, source_year)

        count = 0
        for old_budget in previous_budgets:
            exists = self.get_budget_by_category(user_id, old_budget.category_id, target_month, target_year)
            if not exists:
                self.save_budget(
                    user_id=user_id,
                    category_id=old_budget.category_id,
                    amount=old_budget.amount,
                    month=target_month,
                    year=target_year
                )
                count += 1

        return count

    # ------------------------------------------------------------------
    # NOVO: Alertas de Orçamento
    # ------------------------------------------------------------------

    def get_budget_alerts(
        self,
        user_id: int,
        month: int,
        year: int,
        warning_threshold: float = 80.0,
    ) -> List[BudgetAlert]:
        """
        Retorna alertas para todas as categorias de despesa que possuem
        orçamento definido no período.

        Um alerta é gerado para status WARNING (>= warning_threshold%)
        ou EXCEEDED (>= 100%). Categorias abaixo do limiar retornam
        status 'OK' mas ainda assim aparecem na lista, permitindo
        renderização completa de um painel de metas.

        Args:
            user_id:           ID do usuário
            month:             Mês de referência
            year:              Ano de referência
            warning_threshold: Percentual (0–100) a partir do qual o
                               status muda para WARNING (default 80).

        Returns:
            Lista de BudgetAlert ordenada por pct_used decrescente.
        """
        budgets = self.get_budgets_by_period(user_id, month, year)

        if not budgets:
            return []

        # Consulta o gasto real por categoria em um único round-trip
        spent_by_category = self._get_spent_by_category(user_id, month, year)

        alerts: List[BudgetAlert] = []

        for budget in budgets:
            spent = spent_by_category.get(budget.category_id, 0.0)
            pct   = (spent / budget.amount * 100) if budget.amount > 0 else 0.0

            if pct >= 100:
                status = "EXCEEDED"
            elif pct >= warning_threshold:
                status = "WARNING"
            else:
                status = "OK"

            category_name = (
                budget.category.name
                if hasattr(budget, "category") and budget.category
                else f"Categoria {budget.category_id}"
            )

            alerts.append(BudgetAlert(
                category_id=budget.category_id,
                category_name=category_name,
                budget_amount=round(budget.amount, 2),
                spent_amount=round(spent, 2),
                pct_used=round(pct, 1),
                status=status,
            ))

        return sorted(alerts, key=lambda a: a.pct_used, reverse=True)

    def get_exceeded_budgets(
        self,
        user_id: int,
        month: int,
        year: int,
    ) -> List[BudgetAlert]:
        """
        Atalho: retorna apenas orçamentos com status EXCEEDED.
        Útil para notificações e badges de alerta na sidebar.
        """
        return [
            a for a in self.get_budget_alerts(user_id, month, year)
            if a.status == "EXCEEDED"
        ]

    # ------------------------------------------------------------------
    # Privado
    # ------------------------------------------------------------------

    def _get_spent_by_category(
        self,
        user_id: int,
        month: int,
        year: int,
    ) -> Dict[int, float]:
        """
        Retorna o total gasto (PAID) por category_id para o período.
        Usa uma única query agregada para performance.
        Considera apenas transações do tipo EXPENSE com status PAID.
        """
        from database.models.category import TransactionType

        rows = (
            self.db.query(
                Transaction.category_id,
                func.sum(Transaction.base_amount).label("total"),
            )
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == TransactionType.EXPENSE,
                Transaction.status == TransactionStatus.PAID,
                extract("month", Transaction.paid_date) == month,
                extract("year",  Transaction.paid_date) == year,
            )
            .group_by(Transaction.category_id)
            .all()
        )

        return {row.category_id: float(row.total or 0.0) for row in rows}
