"""
Repository para operações com transações.
"""
from typing import List, Optional, Tuple
from datetime import date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc
from database.models.transaction import Transaction, TransactionStatus
from database.models.category import TransactionType, Category
from database.models.account import Account
from database.repositories.base_repo import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    """
    Repository de transações com queries otimizadas.
    """
    
    def __init__(self, db: Session):
        super().__init__(Transaction, db)
    
    def create_transaction(
        self,
        user_id: int,
        account_id: int,
        category_id: int,
        base_amount: float,
        transaction_type: TransactionType,
        due_date: date,
        description: Optional[str] = None,
        notes: Optional[str] = None,
        interest: float = 0.0,
        discount: float = 0.0,
        cashback: float = 0.0,
        paid_date: Optional[date] = None,
        is_recurring: bool = False,
    ) -> Transaction:
        """
        Cria nova transação.
        
        Args:
            Vários parâmetros da transação
        
        Returns:
            Transaction criada
        """
        # Calcula valor final
        amount = base_amount + interest - discount - cashback
        
        # Define status
        status = TransactionStatus.PAID if paid_date else TransactionStatus.PENDING
        
        return self.create(
            user_id=user_id,
            account_id=account_id,
            category_id=category_id,
            description=description,
            notes=notes,
            base_amount=base_amount,
            amount=amount,
            interest=interest,
            discount=discount,
            cashback=cashback,
            transaction_type=transaction_type,
            status=status,
            due_date=due_date,
            paid_date=paid_date,
            is_recurring=is_recurring,
        )
    
    def get_with_relations(self, transaction_id: int) -> Optional[Transaction]:
        """
        Busca transação com relacionamentos carregados.
        
        Args:
            transaction_id: ID da transação
        
        Returns:
            Transaction com category e account
        """
        return self.db.query(Transaction).options(
            joinedload(Transaction.category),
            joinedload(Transaction.account),
        ).filter(
            Transaction.id == transaction_id,
            Transaction.is_deleted == False,
        ).first()
    
    def filter_transactions(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        transaction_type: Optional[TransactionType] = None,
        status: Optional[TransactionStatus] = None,
        category_ids: Optional[List[int]] = None,
        account_ids: Optional[List[int]] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        search: Optional[str] = None,
        is_recurring: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "due_date",
        sort_desc: bool = True,
    ) -> Tuple[List[Transaction], int]:
        """
        Filtra transações com paginação.
        
        Returns:
            Tupla (lista_transacoes, total_count)
        """
        query = self.db.query(Transaction).options(
            joinedload(Transaction.category),
            joinedload(Transaction.account),
        ).filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted == False,
        )
        
        # Filtros de data
        if start_date:
            query = query.filter(Transaction.due_date >= start_date)
        if end_date:
            query = query.filter(Transaction.due_date <= end_date)
        
        # Filtro de tipo
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)
        
        # Filtro de status
        if status:
            query = query.filter(Transaction.status == status)
        
        # Filtro de categorias
        if category_ids:
            query = query.filter(Transaction.category_id.in_(category_ids))
        
        # Filtro de contas
        if account_ids:
            query = query.filter(Transaction.account_id.in_(account_ids))
        
        # Filtro de valor
        if min_amount is not None:
            query = query.filter(Transaction.amount >= min_amount)
        if max_amount is not None:
            query = query.filter(Transaction.amount <= max_amount)
        
        # Filtro de recorrência
        if is_recurring is not None:
            query = query.filter(Transaction.is_recurring == is_recurring)
        
        # Busca textual
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Transaction.description.ilike(search_term),
                    Transaction.notes.ilike(search_term),
                )
            )
        
        # Total antes da paginação
        total = query.count()
        
        # Ordenação
        order_field = getattr(Transaction, sort_by, Transaction.due_date)
        query = query.order_by(desc(order_field) if sort_desc else order_field)
        
        # Paginação
        offset = (page - 1) * page_size
        transactions = query.offset(offset).limit(page_size).all()
        
        return transactions, total
    
    def sum_by_type(
        self,
        user_id: int,
        transaction_type: TransactionType,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        status: Optional[TransactionStatus] = None,
    ) -> float:
        """
        Soma valores por tipo de transação.
        
        Args:
            user_id: ID do usuário
            transaction_type: INCOME ou EXPENSE
            start_date: Data inicial
            end_date: Data final
            status: Filtrar por status
        
        Returns:
            Soma total
        """
        query = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == transaction_type,
            Transaction.is_deleted == False,
        )
        
        if start_date:
            query = query.filter(Transaction.due_date >= start_date)
        if end_date:
            query = query.filter(Transaction.due_date <= end_date)
        if status:
            query = query.filter(Transaction.status == status)
        
        result = query.scalar()
        return result or 0.0
    
    def get_by_category(
        self,
        user_id: int,
        category_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Transaction]:
        """
        Lista transações de uma categoria.
        
        Args:
            user_id: ID do usuário
            category_id: ID da categoria
            start_date: Data inicial
            end_date: Data final
        
        Returns:
            Lista de transações
        """
        query = self.db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.category_id == category_id,
            Transaction.is_deleted == False,
        )
        
        if start_date:
            query = query.filter(Transaction.due_date >= start_date)
        if end_date:
            query = query.filter(Transaction.due_date <= end_date)
        
        return query.order_by(desc(Transaction.due_date)).all()
    
    def get_overdue(self, user_id: int) -> List[Transaction]:
        """
        Lista transações atrasadas.
        
        Args:
            user_id: ID do usuário
        
        Returns:
            Lista de transações atrasadas
        """
        today = date.today()
        
        return self.db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.status == TransactionStatus.PENDING,
            Transaction.due_date < today,
            Transaction.is_deleted == False,
        ).order_by(Transaction.due_date).all()
    
    def mark_as_paid(
        self,
        transaction_id: int,
        paid_date: Optional[date] = None,
    ) -> bool:
        """
        Marca transação como paga.
        
        Args:
            transaction_id: ID da transação
            paid_date: Data do pagamento (hoje se None)
        
        Returns:
            True se marcado
        """
        transaction = self.get_by_id(transaction_id)
        if not transaction:
            return False
        
        transaction.mark_as_paid(paid_date)
        self.db.flush()
        return True
    
    def get_category_totals(
        self,
        user_id: int,
        transaction_type: TransactionType,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[dict]:
        """
        Retorna totais agrupados por categoria.
        
        Args:
            user_id: ID do usuário
            transaction_type: Tipo de transação
            start_date: Data inicial
            end_date: Data final
        
        Returns:
            Lista de dicts com {category_id, category_name, total, count}
        """
        query = self.db.query(
            Transaction.category_id,
            Category.name,
            func.sum(Transaction.amount).label('total'),
            func.count(Transaction.id).label('count'),
        ).join(
            Category, Transaction.category_id == Category.id
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == transaction_type,
            Transaction.status == TransactionStatus.PAID,
            Transaction.is_deleted == False,
        )
        
        if start_date:
            query = query.filter(Transaction.due_date >= start_date)
        if end_date:
            query = query.filter(Transaction.due_date <= end_date)
        
        results = query.group_by(
            Transaction.category_id,
            Category.name,
        ).order_by(desc('total')).all()
        
        return [
            {
                "category_id": r.category_id,
                "category_name": r.name,
                "total": float(r.total or 0),
                "count": r.count,
            }
            for r in results
        ]
