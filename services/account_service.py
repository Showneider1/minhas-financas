"""
Serviço de gerenciamento de contas — P0 (ADR-002).

- Valores Decimal. `balance` é cache do BalanceService (único escritor).
- Exclusão é soft-delete (is_deleted) — nunca hard delete com lançamentos.
- Todo acesso filtra user_id (anti-IDOR).
"""
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session
from database.models.account import Account
from database.models.transaction import Transaction
from schemas.account_schema import AccountCreate, AccountUpdate
from utils.money import to_money2
import logging

logger = logging.getLogger(__name__)


class AccountService:
    """Serviço para gerenciar contas bancárias."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_account(self, user_id: int, data: AccountCreate) -> Account:
        """Cria uma nova conta para o usuário (saldos Decimal)."""
        try:
            initial = to_money2(data.initial_balance or 0, where="account.create")
            account = Account(
                name=data.name,
                account_type=data.account_type,
                initial_balance=initial,
                balance=initial,
                color=data.color,
                user_id=user_id,
            )
            if data.credit_limit is not None:
                account.credit_limit = to_money2(data.credit_limit, where="account.create")
            if data.closing_day is not None:
                account.closing_day = data.closing_day
            if data.due_day is not None:
                account.due_day = data.due_day
            
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
        """Contas ativas e não excluídas do usuário."""
        return self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.is_deleted.is_(False),
        ).all()
    
    def get_account_by_id(self, account_id: int, user_id: int) -> Optional[Account]:
        """Conta específica do usuário (exclui soft-deleted)."""
        return self.db.query(Account).filter(
            Account.id == account_id,
            Account.user_id == user_id,
            Account.is_deleted.is_(False),
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
        """Soft-delete de conta (nunca hard delete com lançamentos).

        Bloqueia se houver transações vinculadas (preserva histórico).
        """
        account = self.get_account_by_id(account_id, user_id)
        
        if not account:
            return False
        
        try:
            linked = (
                self.db.query(Transaction.id)
                .filter(
                    (Transaction.account_id == account_id)
                    | (Transaction.destination_account_id == account_id)
                )
                .first()
            )
            if linked:
                raise ValueError(
                    "Conta possui lançamentos — desative-a em vez de excluir."
                )
            account.is_deleted = True
            account.is_active = False
            self.db.commit()
            
            logger.info(f"Conta soft-deletada: {account_id}")
            
            return True
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Erro ao deletar conta: {e}")
            raise
    
    def update_balance(self, account_id: int, user_id: int, amount) -> Decimal:
        """Recalcula o saldo via BalanceService (único caminho).

        P0: assinatura anterior sem dono e com float foi removida.
        Movimentações avulsas não são permitidas — o saldo deriva das
        transações (FinanceService/TransferService recalculam no commit).
        """
        from services.balance_service import BalanceService

        _ = to_money2(amount, where="account.update_balance")
        return BalanceService(self.db).recalculate_and_persist(
            account_id, user_id, commit=True
        )
