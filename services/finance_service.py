"""
Serviço de lógica financeira.
"""
from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session
from database.models.transaction import Transaction
from database.models.account import Account
from database.models.category import Category, TransactionType
from schemas.transaction_schema import TransactionCreate, TransactionUpdate
from config.logging_config import app_logger
import logging

logger = logging.getLogger(__name__)


class FinanceService:
    """
    Regras de negócio financeiras.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_transaction(self, user_id: int, data: TransactionCreate) -> Transaction:
        """
        Cria nova transação com validações.
        
        Args:
            user_id: ID do usuário
            data: Dados da transação
        
        Returns:
            Transaction criada
        """
        try:
            # Validações
            if data.base_amount <= 0:
                raise ValueError("Valor deve ser maior que zero")
            
            # Verifica se conta existe
            account = self.db.query(Account).filter(
                Account.id == data.account_id,
                Account.user_id == user_id
            ).first()
            
            if not account:
                raise ValueError("Conta não encontrada")
            
            # Verifica se categoria existe
            category = self.db.query(Category).filter(
                Category.id == data.category_id
            ).first()
            
            if not category:
                raise ValueError("Categoria não encontrada")
            
            logger.info(f"✅ Validações OK - Criando transação...")
            
            # Cria transação
            transaction = Transaction(
                user_id=user_id,
                account_id=data.account_id,
                category_id=data.category_id,
                description=data.description,
                base_amount=data.base_amount,
                transaction_type=data.transaction_type,
                due_date=data.due_date,
                paid_date=data.paid_date,
            )
            
            self.db.add(transaction)
            self.db.flush()  # Garante que o ID seja gerado
            
            logger.info(f"✅ Transação adicionada à sessão - ID: {transaction.id}")
            
            # Atualiza saldo da conta se foi pago
            if data.paid_date:
                if data.transaction_type == TransactionType.INCOME:
                    account.balance += data.base_amount
                else:
                    account.balance -= data.base_amount
                
                logger.info(f"✅ Saldo da conta atualizado: {account.balance}")
            
            # VERIFICAÇÃO: Conta quantas transações existem ANTES do commit
            count_before = self.db.query(Transaction).count()
            print(f"   📊 Transações na sessão ANTES do commit: {count_before}")
            
            # NÃO FAZ COMMIT AQUI! O context manager faz
            logger.info(f"✅ Transação pronta para commit (será feito pelo context manager)")
            
            return transaction
        
        except Exception as e:
            logger.error(f"❌ Erro ao criar transação: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def get_user_transactions(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Transaction]:
        """Retorna transações do usuário."""
        query = self.db.query(Transaction).filter(Transaction.user_id == user_id)
        
        if start_date:
            query = query.filter(Transaction.due_date >= start_date)
        
        if end_date:
            query = query.filter(Transaction.due_date <= end_date)
        
        return query.order_by(Transaction.due_date.desc()).all()
    
    def update_transaction(
        self,
        user_id: int,
        transaction_id: int,
        data: TransactionUpdate,
    ) -> Optional[Transaction]:
        """Atualiza transação."""
        transaction = self.db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id
        ).first()
        
        if not transaction:
            return None
        
        try:
            update_data = data.model_dump(exclude_unset=True)
            
            for key, value in update_data.items():
                setattr(transaction, key, value)
            
            # NÃO FAZ COMMIT - deixa o context manager fazer
            
            logger.info(f"Transação atualizada: {transaction_id}")
            
            return transaction
        
        except Exception as e:
            logger.error(f"Erro ao atualizar transação: {e}")
            raise
    
    def delete_transaction(self, user_id: int, transaction_id: int) -> bool:
        """Deleta transação."""
        transaction = self.db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id
        ).first()
        
        if not transaction:
            return False
        
        try:
            self.db.delete(transaction)
            
            # NÃO FAZ COMMIT - deixa o context manager fazer
            
            logger.info(f"Transação deletada: {transaction_id}")
            
            return True
        
        except Exception as e:
            logger.error(f"Erro ao deletar transação: {e}")
            raise
    
    def mark_transaction_as_paid(
        self,
        user_id: int,
        transaction_id: int,
        paid_date: Optional[date] = None,
    ) -> Optional[Transaction]:
        """
        Marca transação como paga.
        """
        transaction = self.db.query(Transaction).filter(
            Transaction.id == transaction_id,
            Transaction.user_id == user_id
        ).first()
        
        if not transaction:
            return None
        
        try:
            transaction.paid_date = paid_date or date.today()
            
            # Atualiza saldo da conta
            account = self.db.query(Account).filter(Account.id == transaction.account_id).first()
            
            if account:
                if transaction.transaction_type == TransactionType.INCOME:
                    account.balance += transaction.base_amount
                else:
                    account.balance -= transaction.base_amount
            
            # NÃO FAZ COMMIT - deixa o context manager fazer
            
            logger.info(f"Transação marcada como paga: {transaction_id}")
            
            return transaction
        
        except Exception as e:
            logger.error(f"Erro ao marcar transação como paga: {e}")
            raise
    
    def calculate_balance(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> float:
        """
        Calcula saldo total do usuário.
        """
        from sqlalchemy import func
        
        # Receitas
        receitas = self.db.query(func.sum(Transaction.base_amount)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.INCOME,
            Transaction.paid_date.isnot(None)
        )
        
        if start_date:
            receitas = receitas.filter(Transaction.paid_date >= start_date)
        if end_date:
            receitas = receitas.filter(Transaction.paid_date <= end_date)
        
        receitas = receitas.scalar() or 0
        
        # Despesas
        despesas = self.db.query(func.sum(Transaction.base_amount)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.EXPENSE,
            Transaction.paid_date.isnot(None)
        )
        
        if start_date:
            despesas = despesas.filter(Transaction.paid_date >= start_date)
        if end_date:
            despesas = despesas.filter(Transaction.paid_date <= end_date)
        
        despesas = despesas.scalar() or 0
        
        return receitas - despesas
