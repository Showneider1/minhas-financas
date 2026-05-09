"""
Repository robusto para operações com transações.
Correção: filtro de data híbrido no modo ALL (status=None) agora retorna
          transações PAGAS com paid_date no período E PENDENTES com due_date
          no período — evitando o sumiço de pendentes no extrato.
"""
from typing import List, Optional, Tuple
from datetime import date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc, asc
from database.models.transaction import Transaction, TransactionStatus
from database.models.category import TransactionType, Category
from database.repositories.base_repo import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    """
    Repository de transações.
    Gerencia CRUD e regras de negócio de persistência.
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
        Cria uma transação calculando o valor final (amount) automaticamente.
        """
        amount = base_amount + interest - discount - cashback

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
            due_date=due_date,
            paid_date=paid_date,
            is_recurring=is_recurring,
        )

    def get_with_relations(self, transaction_id: int) -> Optional[Transaction]:
        """Busca transação com Account e Category já carregados (Eager Loading)."""
        return self.db.query(Transaction).options(
            joinedload(Transaction.category),
            joinedload(Transaction.account),
        ).filter(
            Transaction.id == transaction_id
        ).first()

    def mark_as_paid(self, transaction_id: int, paid_date: Optional[date] = None) -> bool:
        """
        Marca uma transação como paga. Se nenhuma data for fornecida, usa hoje.
        """
        transaction = self.get_by_id(transaction_id)
        if not transaction:
            return False

        transaction.paid_date = paid_date or date.today()
        self.db.flush()
        return True

    def filter_transactions(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        transaction_type: Optional[TransactionType] = None,
        status: Optional[str] = None,   # 'PAID', 'PENDING' ou None (ALL)
        category_ids: Optional[List[int]] = None,
        account_ids: Optional[List[int]] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        search: Optional[str] = None,
        is_recurring: Optional[bool] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Transaction], int]:
        """
        Motor de busca principal para listagens (Extrato, Relatórios).
        """
        query = self.db.query(Transaction).options(
            joinedload(Transaction.category),
            joinedload(Transaction.account),
        ).filter(Transaction.user_id == user_id)

        # ── 1. Filtro de Data ────────────────────────────────────────────────
        # CORREÇÃO: no modo ALL (status=None) retorna PAGOS com paid_date no
        # período OU PENDENTES com due_date no período.
        # Antes, o modo ALL filtrava só por due_date, fazendo transações pagas
        # cujo due_date caía fora do período sumirem.
        if start_date and end_date:
            s_val = status.value if hasattr(status, "value") else (status or "")

            if s_val == "PAID":
                # Apenas pagos: data de referência = paid_date
                query = query.filter(
                    Transaction.paid_date >= start_date,
                    Transaction.paid_date <= end_date,
                )
            elif s_val == "PENDING":
                # Apenas pendentes: data de referência = due_date
                query = query.filter(
                    Transaction.due_date >= start_date,
                    Transaction.due_date <= end_date,
                )
            else:
                # ALL: mostra PAGOS no período (pela paid_date)
                #       OU PENDENTES no período (pela due_date)
                query = query.filter(
                    or_(
                        and_(
                            Transaction.paid_date.isnot(None),
                            Transaction.paid_date >= start_date,
                            Transaction.paid_date <= end_date,
                        ),
                        and_(
                            Transaction.paid_date.is_(None),
                            Transaction.due_date >= start_date,
                            Transaction.due_date <= end_date,
                        ),
                    )
                )

        # ── 2. Filtros Diretos ───────────────────────────────────────────────
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)

        if category_ids:
            query = query.filter(Transaction.category_id.in_(category_ids))

        if account_ids:
            query = query.filter(Transaction.account_id.in_(account_ids))

        # ── 3. Filtros de Valor ──────────────────────────────────────────────
        if min_amount is not None:
            query = query.filter(Transaction.amount >= min_amount)
        if max_amount is not None:
            query = query.filter(Transaction.amount <= max_amount)

        # ── 4. Filtro de Recorrência ─────────────────────────────────────────
        if is_recurring is not None:
            query = query.filter(Transaction.is_recurring == is_recurring)

        # ── 5. Filtro de Status (paid_date) ──────────────────────────────────
        # Aplicado separadamente do filtro de data para não conflitar com o
        # bloco OR do modo ALL acima.
        if status:
            s_val = status.value if hasattr(status, "value") else status
            if s_val == "PAID":
                query = query.filter(Transaction.paid_date.isnot(None))
            elif s_val == "PENDING":
                query = query.filter(Transaction.paid_date.is_(None))

        # ── 6. Busca Textual ─────────────────────────────────────────────────
        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    Transaction.description.ilike(term),
                    Transaction.notes.ilike(term),
                )
            )

        # ── Paginação e Ordenação ────────────────────────────────────────────
        total = query.count()
        query = query.order_by(desc(Transaction.due_date))

        if page_size:
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)

        return query.all(), total

    def get_filtered(
        self,
        user_id: int,
        start_date: Optional[date],
        end_date: Optional[date],
        account_id: Optional[int],
        category_id: Optional[int],
        status: Optional[str],
        type_: Optional[TransactionType],
    ) -> List[Transaction]:
        """Wrapper simplificado para compatibilidade com o extrato_callbacks."""
        acc_ids = [account_id] if account_id else None
        cat_ids = [category_id] if category_id else None

        txs, _ = self.filter_transactions(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            account_ids=acc_ids,
            category_ids=cat_ids,
            status=status,
            transaction_type=type_,
            page_size=1000,
        )
        return txs

    def sum_by_type(
        self,
        user_id: int,
        transaction_type: TransactionType,
        start_date: date,
        end_date: date,
        status: str,
    ) -> float:
        """Calcula totais para KPIs."""
        query = self.db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == transaction_type,
        )

        is_paid = status in (TransactionStatus.PAID, "PAID")

        if is_paid:
            query = query.filter(
                Transaction.paid_date.isnot(None),
                Transaction.paid_date >= start_date,
                Transaction.paid_date <= end_date,
            )
        else:
            query = query.filter(
                Transaction.paid_date.is_(None),
                Transaction.due_date >= start_date,
                Transaction.due_date <= end_date,
            )

        return query.scalar() or 0.0

    def get_overdue(self, user_id: int) -> List[Transaction]:
        """Retorna transações vencidas e não pagas."""
        today = date.today()
        return self.db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.paid_date.is_(None),
            Transaction.due_date < today,
        ).order_by(asc(Transaction.due_date)).all()

    def get_category_totals(
        self,
        user_id: int,
        transaction_type: TransactionType,
        start_date: date,
        end_date: date,
    ):
        """Agregação para gráficos de pizza."""
        return self.db.query(
            Transaction.category_id,
            Category.name,
            Category.icon,
            Category.color,
            func.sum(Transaction.amount).label("total"),
        ).join(
            Category, Transaction.category_id == Category.id
        ).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == transaction_type,
            Transaction.paid_date.isnot(None),
            Transaction.paid_date >= start_date,
            Transaction.paid_date <= end_date,
        ).group_by(
            Transaction.category_id, Category.name, Category.icon, Category.color,
        ).order_by(desc("total")).all()