"""
Serviço de operações financeiras (transações).
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from database.models.transaction import Transaction, TransactionStatus
from database.models.category import Category, TransactionType
from schemas.transaction_schema import TransactionCreate, TransactionUpdate
from datetime import date


class FinanceService:
    def __init__(self, db_session: Session):
        self.db = db_session

    def create_transaction(self, user_id: int, transaction_data: TransactionCreate):
        """Cria uma nova transação."""
        status_calculado = (
            TransactionStatus.PAID
            if transaction_data.paid_date
            else TransactionStatus.PENDING
        )

        new_transaction = Transaction(
            user_id=user_id,
            description=transaction_data.description,
            base_amount=transaction_data.base_amount,
            transaction_type=transaction_data.transaction_type,
            category_id=transaction_data.category_id,
            account_id=transaction_data.account_id,
            purchase_date=transaction_data.purchase_date,
            due_date=transaction_data.due_date,
            paid_date=transaction_data.paid_date,
            status=status_calculado,
            is_recurring=transaction_data.is_recurring,
            installment_number=transaction_data.installment_number,
            total_installments=transaction_data.total_installments,
            notes=transaction_data.notes,
        )

        self.db.add(new_transaction)
        self.db.commit()
        self.db.refresh(new_transaction)
        return new_transaction

    def update_transaction(
        self, transaction_id: int, user_id: int, transaction_data: TransactionUpdate
    ):
        """
        Atualiza uma transação existente.

        FIX: agora usa TransactionUpdate (todos os campos opcionais) em vez de
        TransactionCreate (todos obrigatórios). Isso permite atualizações
        parciais (PATCH): o frontend só precisa enviar os campos que mudaram.

        A lógica de status (PAID vs PENDING) é recalculada apenas quando
        paid_date está presente no payload, preservando o status atual caso
        o campo não seja enviado.
        """
        transaction = (
            self.db.query(Transaction)
            .filter(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id,
            )
            .first()
        )

        if not transaction:
            raise Exception("Transação não encontrada.")

        # Extrai apenas os campos explicitamente enviados no payload
        update_data = transaction_data.dict(exclude_unset=True)

        # Atualiza cada campo presente no payload
        for field, value in update_data.items():
            setattr(transaction, field, value)

        # Recalcula status somente se paid_date foi enviado no payload
        if "paid_date" in update_data:
            transaction.status = (
                TransactionStatus.PAID
                if update_data["paid_date"]
                else TransactionStatus.PENDING
            )

        self.db.commit()
        self.db.refresh(transaction)
        return transaction

    def get_dashboard_summary(self, user_id: int, month: int, year: int):
        """
        Retorna resumo financeiro do mês separando Realizado de Previsto.
        - Realizado: transações com status PAID no período
        - Previsto:  transações PAID + PENDING com due_date no período
        """
        base_filters_paid = [
            Transaction.user_id == user_id,
            Transaction.status == TransactionStatus.PAID,
            extract("month", Transaction.paid_date) == month,
            extract("year", Transaction.paid_date) == year,
        ]

        base_filters_due = [
            Transaction.user_id == user_id,
            Transaction.status.in_(
                [TransactionStatus.PAID, TransactionStatus.PENDING]
            ),
            extract("month", Transaction.due_date) == month,
            extract("year", Transaction.due_date) == year,
        ]

        # Realizado
        income_real = (
            self.db.query(func.sum(Transaction.base_amount))
            .filter(*base_filters_paid, Transaction.transaction_type == TransactionType.INCOME)
            .scalar() or 0.0
        )
        expense_real = (
            self.db.query(func.sum(Transaction.base_amount))
            .filter(*base_filters_paid, Transaction.transaction_type == TransactionType.EXPENSE)
            .scalar() or 0.0
        )

        # Previsto (inclui pendentes por data de vencimento)
        income_prev = (
            self.db.query(func.sum(Transaction.base_amount))
            .filter(*base_filters_due, Transaction.transaction_type == TransactionType.INCOME)
            .scalar() or 0.0
        )
        expense_prev = (
            self.db.query(func.sum(Transaction.base_amount))
            .filter(*base_filters_due, Transaction.transaction_type == TransactionType.EXPENSE)
            .scalar() or 0.0
        )

        return {
            # Realizado (apenas PAID)
            "income":   income_real,
            "expense":  expense_real,
            "balance":  income_real - expense_real,
            # Previsto (PAID + PENDING por due_date)
            "income_previsto":  income_prev,
            "expense_previsto": expense_prev,
            "balance_previsto": income_prev - expense_prev,
        }
