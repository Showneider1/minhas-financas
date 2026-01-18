"""
Repository para operações com contas.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.models.account import Account
from database.repositories.base_repo import BaseRepository


class AccountRepository(BaseRepository[Account]):
    """
    Repository de contas financeiras.
    """
    
    def __init__(self, db: Session):
        super().__init__(Account, db)
    
    def get_by_user(
        self,
        user_id: int,
        include_inactive: bool = False,
    ) -> List[Account]:
        """
        Lista contas do usuário.
        
        Args:
            user_id: ID do usuário
            include_inactive: Se deve incluir contas inativas
        
        Returns:
            Lista de contas
        """
        query = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_deleted == False
        )
        
        if not include_inactive:
            query = query.filter(Account.is_active == True)
        
        return query.order_by(Account.name).all()
    
    def get_by_user_and_id(
        self,
        user_id: int,
        account_id: int,
    ) -> Optional[Account]:
        """
        Busca conta específica do usuário.
        
        Args:
            user_id: ID do usuário
            account_id: ID da conta
        
        Returns:
            Account ou None
        """
        return self.db.query(Account).filter(
            Account.id == account_id,
            Account.user_id == user_id,
            Account.is_deleted == False
        ).first()
    
    def create_account(
        self,
        user_id: int,
        name: str,
        account_type: str,
        initial_balance: float = 0.0,
        currency: str = "BRL",
    ) -> Account:
        """
        Cria nova conta.
        
        Args:
            user_id: ID do usuário
            name: Nome da conta
            account_type: Tipo da conta
            initial_balance: Saldo inicial
            currency: Moeda
        
        Returns:
            Account criada
        """
        return self.create(
            user_id=user_id,
            name=name,
            account_type=account_type,
            balance=initial_balance,
            initial_balance=initial_balance,
            currency=currency,
            is_active=True,
        )
    
    def update_balance(self, account_id: int, amount: float) -> bool:
        """
        Atualiza saldo da conta.
        
        Args:
            account_id: ID da conta
            amount: Valor a adicionar (negativo para subtrair)
        
        Returns:
            True se atualizado
        """
        account = self.get_by_id(account_id)
        if not account:
            return False
        
        account.update_balance(amount)
        self.db.flush()
        return True
    
    def recalculate_balance(self, account_id: int) -> Optional[float]:
        """
        Recalcula saldo da conta baseado nas transações.
        
        Args:
            account_id: ID da conta
        
        Returns:
            Novo saldo ou None se conta não existe
        """
        from database.models.transaction import Transaction, TransactionStatus
        from database.models.category import TransactionType
        
        account = self.get_by_id(account_id)
        if not account:
            return None
        
        # Soma receitas pagas
        income = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.account_id == account_id,
            Transaction.transaction_type == TransactionType.INCOME,
            Transaction.status == TransactionStatus.PAID,
            Transaction.is_deleted == False,
        ).scalar() or 0.0
        
        # Soma despesas pagas
        expense = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.account_id == account_id,
            Transaction.transaction_type == TransactionType.EXPENSE,
            Transaction.status == TransactionStatus.PAID,
            Transaction.is_deleted == False,
        ).scalar() or 0.0
        
        # Calcula novo saldo
        new_balance = account.initial_balance + income - expense
        account.balance = new_balance
        self.db.flush()
        
        return new_balance
    
    def get_total_balance(self, user_id: int) -> float:
        """
        Calcula saldo total de todas as contas do usuário.
        
        Args:
            user_id: ID do usuário
        
        Returns:
            Saldo total
        """
        result = self.db.query(func.sum(Account.balance)).filter(
            Account.user_id == user_id,
            Account.is_active == True,
            Account.is_deleted == False,
        ).scalar()
        
        return result or 0.0
    
    def toggle_active(self, account_id: int) -> bool:
        """
        Alterna status ativo/inativo da conta.
        
        Args:
            account_id: ID da conta
        
        Returns:
            True se alterado
        """
        account = self.get_by_id(account_id)
        if not account:
            return False
        
        account.is_active = not account.is_active
        self.db.flush()
        return True
