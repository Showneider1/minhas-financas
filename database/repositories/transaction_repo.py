"""
Repository de transações — contrato canônico (P0 — ADR-002).

- Valor: APENAS `base_amount` (Numeric/Decimal). `amount/interest/discount/
  cashback` foram removidos (nunca existiram no model — CODE_AUDIT C1).
- "Pago" ≡ status==PAID AND paid_date IS NOT NULL (sincronizados em escrita).
- TRANSFER excluído das agregações de receita/despesa.
- Acesso com dono: get_owned / mark_as_paid_owned (anti-IDOR).
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import and_, asc, case, desc, func, or_
from sqlalchemy.orm import Session, joinedload

from database.models.category import Category, TransactionType
from database.models.transaction import Transaction, TransactionStatus
from database.repositories.base_repo import BaseRepository
from utils.money import to_money2


class TransactionRepository(BaseRepository[Transaction]):
    """
    Repository de transações.
    Gerencia CRUD e regras de negócio de persistência.
    """

    def __init__(self, db: Session):
        super().__init__(Transaction, db)

    def get_with_relations(self, transaction_id: int, user_id: int) -> Transaction | None:
        """Busca com Account/Category Eager + filtro de dono (anti-IDOR)."""
        return (
            self.db.query(Transaction)
            .options(
                joinedload(Transaction.category),
                joinedload(Transaction.account),
            )
            .filter(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id,
            )
            .first()
        )

    def mark_as_paid(
        self,
        transaction_id: int,
        user_id: int,
        paid_date: date | None = None,
    ) -> bool:
        """Marca como paga sincronizando status + paid_date (idempotente)."""
        transaction = self.get_owned(transaction_id, user_id)
        if not transaction:
            return False
        if transaction.status == TransactionStatus.PAID and transaction.paid_date is not None:
            return True
        transaction.paid_date = paid_date or date.today()
        transaction.status = TransactionStatus.PAID
        self.db.flush()
        return True

    def _build_filtered_query(
        self,
        *,
        user_id: int,
        start_date: date | None,
        end_date: date | None,
        transaction_type: TransactionType | None,
        status: str | None,
        category_ids: list[int] | None,
        account_ids: list[int] | None,
        min_amount,
        max_amount,
        search: str | None,
        is_recurring: bool | None,
    ):
        query = self.db.query(Transaction).filter(Transaction.user_id == user_id)

        s_val = status.value if hasattr(status, "value") else (status or "")

        if start_date and end_date:
            if s_val == "PAID":
                query = query.filter(
                    Transaction.paid_date >= start_date,
                    Transaction.paid_date <= end_date,
                )
            elif s_val == "PENDING":
                query = query.filter(
                    Transaction.due_date >= start_date,
                    Transaction.due_date <= end_date,
                )
            else:
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

        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)

        if category_ids:
            query = query.filter(Transaction.category_id.in_(category_ids))

        if account_ids:
            query = query.filter(Transaction.account_id.in_(account_ids))

        if min_amount is not None:
            query = query.filter(
                Transaction.base_amount >= to_money2(min_amount, where="tx_repo.filter")
            )

        if max_amount is not None:
            query = query.filter(
                Transaction.base_amount <= to_money2(max_amount, where="tx_repo.filter")
            )

        if is_recurring is not None:
            query = query.filter(Transaction.is_recurring == is_recurring)

        if status:
            s_val = status.value if hasattr(status, "value") else status
            if s_val == "PAID":
                query = query.filter(Transaction.paid_date.isnot(None))
            elif s_val == "PENDING":
                query = query.filter(Transaction.paid_date.is_(None))
            elif s_val == "OVERDUE":
                query = query.filter(
                    Transaction.paid_date.is_(None),
                    Transaction.due_date < date.today(),
                )

        if search:
            term = f"%{search[:100]}%"
            query = query.filter(
                or_(
                    Transaction.description.ilike(term),
                    Transaction.notes.ilike(term),
                )
            )

        return query

    def filter_transactions(
        self,
        user_id: int,
        start_date: date | None = None,
        end_date: date | None = None,
        transaction_type: TransactionType | None = None,
        status: str | None = None,
        category_ids: list[int] | None = None,
        account_ids: list[int] | None = None,
        min_amount=None,
        max_amount=None,
        search: str | None = None,
        is_recurring: bool | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Transaction], int]:
        """Busca paginada com eager loading de Category/Account (sem N+1)."""
        query = self._build_filtered_query(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            transaction_type=transaction_type,
            status=status,
            category_ids=category_ids,
            account_ids=account_ids,
            min_amount=min_amount,
            max_amount=max_amount,
            search=search,
            is_recurring=is_recurring,
        ).options(
            joinedload(Transaction.category),
            joinedload(Transaction.account),
        )

        total = query.count()
        query = query.order_by(desc(Transaction.due_date))

        if page_size:
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)

        return query.all(), total

    def get_filtered_summary(
        self,
        *,
        user_id: int,
        start_date: date | None,
        end_date: date | None,
        transaction_type: TransactionType | None,
        status: str | None,
        category_ids: list[int] | None,
        account_ids: list[int] | None,
        search: str | None,
        is_recurring: bool | None = None,
    ) -> dict[str, Decimal | int]:
        """Totais agregados no banco (evita carregar todas as transações)."""
        query = self._build_filtered_query(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            transaction_type=transaction_type,
            status=status,
            category_ids=category_ids,
            account_ids=account_ids,
            min_amount=None,
            max_amount=None,
            search=search,
            is_recurring=is_recurring,
        )

        subquery = query.subquery()
        income_sum = func.sum(
            case(
                (subquery.c.transaction_type == TransactionType.INCOME, subquery.c.base_amount),
                else_=Decimal("0"),
            )
        )
        expense_sum = func.sum(
            case(
                (
                    subquery.c.transaction_type == TransactionType.EXPENSE,
                    subquery.c.base_amount,
                ),
                else_=Decimal("0"),
            )
        )
        pending_expense_sum = func.sum(
            case(
                (
                    and_(
                        subquery.c.transaction_type == TransactionType.EXPENSE,
                        subquery.c.paid_date.is_(None),
                    ),
                    subquery.c.base_amount,
                ),
                else_=Decimal("0"),
            )
        )

        row = (
            self.db.query(
                func.count(subquery.c.id),
                func.coalesce(income_sum, Decimal("0")),
                func.coalesce(expense_sum, Decimal("0")),
                func.coalesce(pending_expense_sum, Decimal("0")),
            )
            .select_from(subquery)
            .one()
        )

        total, income, expense, pending_expense = row
        return {
            "total": int(total or 0),
            "income": to_money2(income or 0, where="tx_repo.summary.income"),
            "expense": to_money2(expense or 0, where="tx_repo.summary.expense"),
            "pending_expense": to_money2(
                pending_expense or 0, where="tx_repo.summary.pending_expense"
            ),
        }

    def export_filtered_transactions(
        self,
        *,
        user_id: int,
        start_date: date | None,
        end_date: date | None,
        transaction_type: TransactionType | None,
        status: str | None,
        category_ids: list[int] | None,
        account_ids: list[int] | None,
        search: str | None,
        is_recurring: bool | None = None,
    ) -> list[Transaction]:
        """Consulta completa para exportação, reaproveitando os filtros da UI.

        - Sem `LIMIT/OFFSET`: o relatório deve conter todos os resultados.
        - `joinedload` evita N+1 ao montar as colunas Categoria/Conta.
        - `user_id` é obrigatório (isolamento anti-IDOR).
        """
        query = self._build_filtered_query(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            transaction_type=transaction_type,
            status=status,
            category_ids=category_ids,
            account_ids=account_ids,
            min_amount=None,
            max_amount=None,
            search=search,
            is_recurring=is_recurring,
        ).options(
            joinedload(Transaction.category),
            joinedload(Transaction.account),
        )

        return query.order_by(desc(Transaction.due_date)).all()

    def get_filtered(
        self,
        user_id: int,
        start_date: date | None,
        end_date: date | None,
        account_id: int | None,
        category_id: int | None,
        status: str | None,
        type_: TransactionType | None,
    ) -> list[Transaction]:
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
            page_size=10000,
        )
        return txs

    def sum_by_type(
        self,
        user_id: int,
        transaction_type: TransactionType,
        start_date: date,
        end_date: date,
        status: str,
    ) -> Decimal:
        """Totais para KPIs (canônico: base_amount; TRANSFER excluído por tipo)."""
        query = self.db.query(func.sum(Transaction.base_amount)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == transaction_type,
        )

        is_paid = status in (TransactionStatus.PAID, "PAID")

        if is_paid:
            query = query.filter(
                Transaction.status == TransactionStatus.PAID,
                Transaction.paid_date.isnot(None),
                Transaction.paid_date >= start_date,
                Transaction.paid_date <= end_date,
            )
        else:
            query = query.filter(
                Transaction.status == TransactionStatus.PENDING,
                Transaction.paid_date.is_(None),
                Transaction.due_date >= start_date,
                Transaction.due_date <= end_date,
            )

        return to_money2(query.scalar() or 0, where="tx_repo.sum")

    def get_overdue(self, user_id: int) -> list[Transaction]:
        """Vencidas e não pagas (exclui CANCELLED)."""
        today = date.today()
        return (
            self.db.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.status == TransactionStatus.PENDING,
                Transaction.paid_date.is_(None),
                Transaction.due_date < today,
            )
            .order_by(asc(Transaction.due_date))
            .all()
        )

    def get_category_totals(
        self,
        user_id: int,
        transaction_type: TransactionType,
        start_date: date,
        end_date: date,
    ):
        """Agregação para gráficos (canônico: base_amount; só pagas)."""
        return (
            self.db.query(
                Transaction.category_id,
                Category.name,
                Category.icon,
                Category.color,
                func.sum(Transaction.base_amount).label("total"),
            )
            .join(Category, Transaction.category_id == Category.id)
            .filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == transaction_type,
                Transaction.status == TransactionStatus.PAID,
                Transaction.paid_date.isnot(None),
                Transaction.paid_date >= start_date,
                Transaction.paid_date <= end_date,
            )
            .group_by(
                Transaction.category_id,
                Category.name,
                Category.icon,
                Category.color,
            )
            .order_by(desc("total"))
            .all()
        )
