from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from database.models.budget import Budget
from typing import List, Optional

class BudgetService:
    def __init__(self, db_session: Session):
        self.db = db_session

    def save_budget(self, user_id: int, category_id: int, amount: float, month: int, year: int) -> Budget:
        """
        Cria ou Atualiza (Upsert) uma meta.
        Se já existe meta para aquela categoria naquele mês, apenas atualiza o valor.
        """
        # 1. Busca meta existente
        existing_budget = self.db.query(Budget).filter(
            Budget.user_id == user_id,
            Budget.category_id == category_id,
            Budget.month == month,
            Budget.year == year
        ).first()

        if existing_budget:
            # ATUALIZA
            existing_budget.amount = amount
            result = existing_budget
        else:
            # CRIA NOVA
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
        """
        Retorna todas as metas definidas para um mês/ano específico.
        """
        return self.db.query(Budget).filter(
            Budget.user_id == user_id,
            Budget.month == month,
            Budget.year == year
        ).all()

    def get_budget_by_category(self, user_id: int, category_id: int, month: int, year: int) -> Optional[Budget]:
        """
        Retorna uma meta específica de uma categoria.
        """
        return self.db.query(Budget).filter(
            Budget.user_id == user_id,
            Budget.category_id == category_id,
            Budget.month == month,
            Budget.year == year
        ).first()

    def delete_budget(self, user_id: int, budget_id: int) -> bool:
        """
        Remove uma meta.
        """
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
        Recurso Inteligente: Copia todas as metas do mês anterior para o mês atual.
        Retorna o número de metas copiadas.
        Útil para não ter que cadastrar tudo de novo todo mês.
        """
        # 1. Calcular mês anterior
        if target_month == 1:
            source_month = 12
            source_year = target_year - 1
        else:
            source_month = target_month - 1
            source_year = target_year

        # 2. Buscar metas do mês anterior
        previous_budgets = self.get_budgets_by_period(user_id, source_month, source_year)
        
        count = 0
        for old_budget in previous_budgets:
            # Verifica se já existe meta no mês novo para não sobrescrever
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