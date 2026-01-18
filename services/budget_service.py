from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from database.models.budget import Budget
from database.models.transaction import Transaction
from database.models.category import Category
from schemas.budget_schema import BudgetCreate, BudgetResponse

class BudgetService:
    def __init__(self, db: Session):
        self.db = db

    def create_or_update_budget(self, user_id: int, budget_data: BudgetCreate):
        """Cria ou atualiza uma meta para uma categoria."""
        existing_budget = self.db.query(Budget).filter(
            Budget.user_id == user_id,
            Budget.category_id == budget_data.category_id
        ).first()

        if existing_budget:
            existing_budget.amount = budget_data.amount
            self.db.commit()
            self.db.refresh(existing_budget)
            return existing_budget
        
        new_budget = Budget(
            user_id=user_id,
            category_id=budget_data.category_id,
            amount=budget_data.amount
        )
        self.db.add(new_budget)
        self.db.commit()
        self.db.refresh(new_budget)
        return new_budget

    def get_user_budgets_status(self, user_id: int, month: int, year: int):
        """
        Retorna todas as metas do usuário com o status atual (gasto vs limite).
        """
        # 1. Buscar todas as metas do usuário
        budgets = self.db.query(Budget).filter(Budget.user_id == user_id).all()
        
        results = []
        
        for budget in budgets:
            # 2. Calcular gasto total da categoria no mês atual
            total_spent = self.db.query(func.sum(Transaction.base_amount)).filter(
                Transaction.user_id == user_id,
                Transaction.category_id == budget.category_id,
                Transaction.transaction_type == "EXPENSE",
                func.extract('month', Transaction.paid_date) == month,
                func.extract('year', Transaction.paid_date) == year
            ).scalar() or 0.0
            
            percentage = (total_spent / budget.amount) * 100 if budget.amount > 0 else 0
            
            results.append(BudgetResponse(
                id=budget.id,
                category_name=budget.category.name,
                category_icon=budget.category.icon,
                amount=budget.amount,
                spent=total_spent,
                percentage=min(percentage, 100) # Trava em 100% visualmente
            ))
            
        return results