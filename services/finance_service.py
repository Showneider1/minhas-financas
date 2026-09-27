"""
Serviço de operações financeiras (transações) — P0 (ADR-002).

Contrato:
- `base_amount: Decimal` é o único valor (validado pelo schema TransactionCreate).
- TRANSFER é criado apenas via TransferService (aqui: rejeitado com orientação).
- "Pago" sincronizado: status=PAID ⟺ paid_date preenchido.
- Saldos: BalanceService.recalculate_and_persist nas contas afetadas, mesmo commit.
- Isolamento: todo acesso filtra user_id (IDOR — Fase 7).
- Erros: rollback explícito + exceção tipada (nunca str(e) vazar SQL).
"""

from datetime import date

from sqlalchemy.orm import Session

from database.models.account import Account
from database.models.category import TransactionType
from database.models.transaction import Transaction, TransactionStatus
from schemas.transaction_schema import TransactionCreate, TransactionUpdate
from services.balance_service import BalanceService
from utils.money import to_money2


class TransactionNotFound(LookupError):
    """Transação inexistente ou de outro usuário (não distinguir — anti-enumeração)."""


class FinanceService:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.balances = BalanceService(db_session)

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------
    def create_transaction(self, user_id: int, transaction_data: TransactionCreate):
        """Cria transação comum (INCOME/EXPENSE). TRANSFER → TransferService."""
        # P1: enums unificados (database.enums) — comparação direta por identidade.
        tx_type = transaction_data.transaction_type
        if tx_type == TransactionType.TRANSFER:
            raise ValueError(
                "TRANSFER deve ser criado via TransferService.transfer "
                "(origem, destino e idempotência)."
            )
        account = self._owned_account(user_id, transaction_data.account_id)
        category = self._owned_category(user_id, transaction_data.category_id)
        # P0: categoria deve ser do mesmo tipo do lançamento (ex.: receita com
        # categoria de receita). Categorias sem tipo (NULL) aceitam qualquer.
        if category.transaction_type is not None and category.transaction_type != tx_type:
            raise ValueError("Categoria incompatível com o tipo do lançamento.")

        value = to_money2(transaction_data.base_amount, where="finance.create")
        paid = transaction_data.paid_date is not None

        tx = Transaction(
            user_id=user_id,
            description=transaction_data.description,
            base_amount=value,
            transaction_type=tx_type,
            category_id=transaction_data.category_id,
            account_id=transaction_data.account_id,
            purchase_date=transaction_data.purchase_date,
            due_date=transaction_data.due_date,
            paid_date=transaction_data.paid_date,
            status=TransactionStatus.PAID if paid else TransactionStatus.PENDING,
            is_recurring=transaction_data.is_recurring,
            installment_number=transaction_data.installment_number,
            total_installments=transaction_data.total_installments,
            notes=transaction_data.notes,
        )
        try:
            self.db.add(tx)
            self.db.flush()
            self.balances.recalculate_and_persist(account.id, user_id)
            self.db.commit()
            self.db.refresh(tx)
        except Exception:
            self.db.rollback()
            raise
        return tx

    def update_transaction(
        self, transaction_id: int, user_id: int, transaction_data: TransactionUpdate
    ):
        """Atualização parcial (PATCH) com user_id obrigatório.

        TRANSFER não pode ser convertido nem editado aqui (usa TransferService).
        """
        tx = self._owned(transaction_id, user_id)
        if tx.transaction_type == TransactionType.TRANSFER:
            raise ValueError("TRANSFER é gerenciado pelo TransferService.")

        update_data = transaction_data.dict(exclude_unset=True)

        if "transaction_type" in update_data and update_data["transaction_type"] is not None:
            if update_data["transaction_type"] == TransactionType.TRANSFER:
                raise ValueError("Conversão para TRANSFER não permitida aqui.")
        if "base_amount" in update_data and update_data["base_amount"] is not None:
            update_data["base_amount"] = to_money2(
                update_data["base_amount"], where="finance.update"
            )
        if "account_id" in update_data and update_data["account_id"] is not None:
            self._owned_account(user_id, update_data["account_id"])
        if "category_id" in update_data and update_data["category_id"] is not None:
            new_cat = self._owned_category(user_id, update_data["category_id"])
            new_type = update_data.get("transaction_type", tx.transaction_type)
            if new_cat.transaction_type is not None and new_cat.transaction_type != new_type:
                raise ValueError("Categoria incompatível com o tipo do lançamento.")
        if update_data.get("destination_account_id") is not None:
            raise ValueError(
                "destination_account_id é exclusivo de TRANSFER (use TransferService)."
            )

        old_account = tx.account_id
        for field, value in update_data.items():
            setattr(tx, field, value)

        if "paid_date" in update_data:
            tx.status = (
                TransactionStatus.PAID if update_data["paid_date"] else TransactionStatus.PENDING
            )

        try:
            self.db.flush()
            self.balances.recalculate_and_persist(old_account, user_id)
            if tx.account_id != old_account:
                self.balances.recalculate_and_persist(tx.account_id, user_id)
            self.db.commit()
            self.db.refresh(tx)
        except Exception:
            self.db.rollback()
            raise
        return tx

    def delete_transaction(self, transaction_id: int, user_id: int) -> bool:
        """Exclusão com isolamento por usuário + recálculo de saldos.

        TRANSFER pago recalcula origem E destino. Retorna True; levanta
        TransactionNotFound se inexistente/de outro usuário.
        """
        tx = self._owned(transaction_id, user_id)
        accounts = {tx.account_id}
        if tx.destination_account_id:
            accounts.add(tx.destination_account_id)
        try:
            self.db.delete(tx)
            self.db.flush()
            for acc_id in accounts:
                self.balances.touch_account(acc_id, user_id)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return True

    def mark_as_paid(
        self,
        transaction_id: int,
        user_id: int,
        paid_date: date | None = None,
    ):
        """Efetiva transação (sincroniza status + paid_date). Idempotente.

        CANCELLED nunca ressuscita (levanta erro).
        """
        tx = self._owned(transaction_id, user_id)
        if tx.status == TransactionStatus.CANCELLED:
            raise ValueError("Transação cancelada não pode ser efetivada.")
        if tx.transaction_type == TransactionType.TRANSFER:
            from services.transfer_service import TransferService

            return TransferService(self.db).confirm_transfer(transaction_id, user_id, paid_date)
        if tx.status == TransactionStatus.PAID and tx.paid_date is not None:
            return tx
        tx.paid_date = paid_date or date.today()
        tx.status = TransactionStatus.PAID
        try:
            self.db.flush()
            self.balances.recalculate_and_persist(tx.account_id, user_id)
            self.db.commit()
            self.db.refresh(tx)
        except Exception:
            self.db.rollback()
            raise
        return tx

    # ------------------------------------------------------------------
    # Leitura (resumo mensal — delega aos filtros canônicos)
    # ------------------------------------------------------------------
    def get_dashboard_summary(self, user_id: int, month: int, year: int):
        """Resumo do mês — delega ao BalanceService (regra única, Fase 6).

        Mantém as chaves legadas (`income`, `expense`, `balance`,
        `income_previsto`, ...) com valores Decimal.
        """
        from calendar import monthrange

        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        summary = self.balances.get_period_summary(user_id, start, end)
        income_real = summary["income_paid"]
        expense_real = summary["expense_paid"]
        income_prev = summary["income_pending"] + income_real
        expense_prev = summary["expense_pending"] + expense_real
        return {
            "income": income_real,
            "expense": expense_real,
            "balance": income_real - expense_real,
            "income_previsto": income_prev,
            "expense_previsto": expense_prev,
            "balance_previsto": income_prev - expense_prev,
        }

    # ------------------------------------------------------------------
    # Helpers (isolamento)
    # ------------------------------------------------------------------
    def _owned(self, transaction_id: int, user_id: int) -> Transaction:
        tx = (
            self.db.query(Transaction)
            .filter(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id,
            )
            .first()
        )
        if not tx:
            raise TransactionNotFound("Transação não encontrada.")
        return tx

    def _owned_account(self, user_id: int, account_id: int) -> Account:
        acc = (
            self.db.query(Account)
            .filter(Account.id == account_id, Account.user_id == user_id)
            .first()
        )
        if not acc:
            raise TransactionNotFound("Conta não encontrada para este usuário.")
        return acc

    def _owned_category(self, user_id: int, category_id: int):
        from database.models.category import Category

        cat = (
            self.db.query(Category)
            .filter(
                Category.id == category_id,
            )
            .first()
        )
        # Categorias podem ser do sistema (user_id NULL) ou do usuário.
        if not cat or (cat.user_id is not None and cat.user_id != user_id):
            raise TransactionNotFound("Categoria não encontrada para este usuário.")
        return cat
