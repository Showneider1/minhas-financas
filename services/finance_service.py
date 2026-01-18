from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from database.models.transaction import Transaction
from database.models.category import Category, TransactionType
from schemas.transaction_schema import TransactionCreate, TransactionFilter
from datetime import date

class FinanceService:
    def __init__(self, db_session: Session):
        self.db = db_session

    def create_transaction(self, user_id: int, transaction_data: TransactionCreate):
        """Cria uma nova transação."""
        new_transaction = Transaction(
            user_id=user_id,
            description=transaction_data.description,
            base_amount=transaction_data.base_amount,
            transaction_type=transaction_data.transaction_type,
            category_id=transaction_data.category_id,
            account_id=transaction_data.account_id,
            due_date=transaction_data.due_date,
            paid_date=transaction_data.paid_date
            # REMOVIDO: status=... (O Model calcula isso sozinho)
        )
        self.db.add(new_transaction)
        self.db.commit()
        self.db.refresh(new_transaction)
        return new_transaction

    def update_transaction(self, transaction_id: int, user_id: int, transaction_data: TransactionCreate):
        """Atualiza uma transação existente."""
        # Busca transação e verifica se pertence ao usuário
        transaction = self.db.query(Transaction).filter(
            Transaction.id == transaction_id, 
            Transaction.user_id == user_id
        ).first()

        if not transaction:
            raise Exception("Transação não encontrada ou acesso negado.")

        # Atualiza os campos
        transaction.description = transaction_data.description
        transaction.base_amount = transaction_data.base_amount
        transaction.transaction_type = transaction_data.transaction_type
        transaction.category_id = transaction_data.category_id
        transaction.account_id = transaction_data.account_id
        transaction.due_date = transaction_data.due_date
        transaction.paid_date = transaction_data.paid_date
        
        # REMOVIDO: transaction.status = ... (O Model calcula isso sozinho)

        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def get_dashboard_summary(self, user_id: int, month: int, year: int):
        """Retorna resumo para os cards do dashboard."""
        
        # Receitas
        income = self.db.query(func.sum(Transaction.base_amount)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.INCOME,
            Transaction.paid_date.isnot(None),
            extract('month', Transaction.paid_date) == month,
            extract('year', Transaction.paid_date) == year
        ).scalar() or 0.0

        # Despesas
        expense = self.db.query(func.sum(Transaction.base_amount)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.EXPENSE,
            Transaction.paid_date.isnot(None),
            extract('month', Transaction.paid_date) == month,
            extract('year', Transaction.paid_date) == year
        ).scalar() or 0.0

        return {
            "income": income,
            "expense": expense,
            "balance": income - expense
        }