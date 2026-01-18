"""
Serviço de gerenciamento de contas.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from database.models.account import Account, AccountType
from schemas.account_schema import AccountCreate, AccountUpdate
import logging

logger = logging.getLogger(__name__)


class AccountService:
    """Serviço para gerenciar contas bancárias."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_account(self, user_id: int, data: AccountCreate) -> Account:
        """Cria uma nova conta para o usuário."""
        try:
            account = Account(
                name=data.name,
                account_type=data.account_type,
                initial_balance=data.initial_balance,
                balance=data.initial_balance,
                color=data.color,
                user_id=user_id,
            )
            
            self.db.add(account)
            self.db.flush()  # Garante que o ID seja gerado
            
            account_id = account.id  # Salva o ID antes do commit
            
            self.db.commit()
            
            logger.info(f"Conta criada: {account_id} - Usuário: {user_id}")
            
            # Retorna o objeto (sem refresh)
            return account
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao criar conta: {e}")
            raise
    
    def get_user_accounts(self, user_id: int) -> List[Account]:
        """Retorna todas as contas de um usuário."""
        return self.db.query(Account).filter(Account.user_id == user_id).all()
    
    def get_account_by_id(self, account_id: int, user_id: int) -> Optional[Account]:
        """Retorna uma conta específica do usuário."""
        return self.db.query(Account).filter(
            Account.id == account_id,
            Account.user_id == user_id
        ).first()
    
    def update_account(self, account_id: int, user_id: int, data: AccountUpdate) -> Optional[Account]:
        """Atualiza uma conta."""
        account = self.get_account_by_id(account_id, user_id)
        
        if not account:
            return None
        
        try:
            if data.name is not None:
                account.name = data.name
            if data.account_type is not None:
                account.account_type = data.account_type
            if data.color is not None:
                account.color = data.color
            
            self.db.commit()
            
            logger.info(f"Conta atualizada: {account_id}")
            
            return account
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar conta: {e}")
            raise
    
    def delete_account(self, account_id: int, user_id: int) -> bool:
        """Deleta uma conta (soft delete)."""
        account = self.get_account_by_id(account_id, user_id)
        
        if not account:
            return False
        
        try:
            self.db.delete(account)
            self.db.commit()
            
            logger.info(f"Conta deletada: {account_id}")
            
            return True
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao deletar conta: {e}")
            raise
    
    def update_balance(self, account_id: int, amount: float, operation: str = "add") -> bool:
        """
        Atualiza o saldo de uma conta.
        
        Args:
            account_id: ID da conta
            amount: Valor a ser adicionado/subtraído
            operation: "add" para adicionar, "subtract" para subtrair
        """
        try:
            account = self.db.query(Account).filter(Account.id == account_id).first()
            
            if not account:
                return False
            
            if operation == "add":
                account.balance += amount
            elif operation == "subtract":
                account.balance -= amount
            
            self.db.commit()
            
            logger.info(f"Saldo atualizado: Conta {account_id} - Novo saldo: {account.balance}")
            
            return True
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao atualizar saldo: {e}")
            raise
