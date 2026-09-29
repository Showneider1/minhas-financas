"""
Serviço central de saldos (P0 — ADR-002, Fase 6).

REGRA CANÔNICA ÚNICA (todas as telas consomem este serviço):

    saldo_conta(A) = initial_balance(A)
        + SUM(base_amount WHERE type=INCOME  AND pago AND account_id=A)
        - SUM(base_amount WHERE type=EXPENSE AND pago AND account_id=A)
        + SUM(base_amount WHERE type=TRANSFER AND pago AND destination=A)
        - SUM(base_amount WHERE type=TRANSFER AND pago AND account_id=A)

    pago ≡ status == PAID AND paid_date IS NOT NULL
    TRANSFER movimenta duas contas sem ser receita/despesa (fora dos KPIs).
    CANCELLED nunca entra.

`Account.balance` é CACHE persistido desta fórmula — o único escritor é
`recalculate_and_persist()`. Nenhum outro código atribui `balance` à mão.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from database.models.account import Account, AccountType
from database.models.category import TransactionType
from database.models.transaction import Transaction, TransactionStatus
from utils.money import to_money2

ZERO = Decimal("0.00")
# Tipos que compõem receita/despesa. TRANSFER é excluído por construção.
RESULT_TYPES = (TransactionType.INCOME, TransactionType.EXPENSE)


def _paid_filter():
    """Filtro canônico de 'pago' (status sincronizado com paid_date)."""
    return (
        Transaction.status == TransactionStatus.PAID,
        Transaction.paid_date.isnot(None),
    )


class BalanceService:
    """Fonte única de saldos e resumos de período."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Saldos
    # ------------------------------------------------------------------
    def get_account_balance(self, account_id: int, user_id: int) -> Decimal:
        """Saldo calculado da conta (não persiste). Levanta se conta não é do usuário."""
        account = (
            self.db.query(Account)
            .filter(Account.id == account_id, Account.user_id == user_id)
            .first()
        )
        if not account:
            raise LookupError("Conta não encontrada para este usuário.")
        return self._compute(account, user_id)

    def _compute(self, account: Account, user_id: int) -> Decimal:
        initial = to_money2(account.initial_balance or 0, where="balance.initial")
        income = self._sum(account.id, user_id, TransactionType.INCOME)
        expense = self._sum(account.id, user_id, TransactionType.EXPENSE)
        # Transferências: crédito quando destino, débito quando origem (pagas).
        # Não são receita/despesa — entram aqui, nunca nos KPIs de período.
        tin = self._transfer_sum(account.id, user_id, incoming=True)
        tout = self._transfer_sum(account.id, user_id, incoming=False)
        return (initial + income - expense + tin - tout).quantize(Decimal("0.01"))

    def _sum(self, account_id: int, user_id: int, type_: TransactionType) -> Decimal:
        total = (
            self.db.query(func.sum(Transaction.base_amount))
            .filter(
                Transaction.account_id == account_id,
                Transaction.user_id == user_id,  # defense-in-depth (anti-IDOR)
                Transaction.transaction_type == type_,
                *_paid_filter(),
            )
            .scalar()
        )
        return to_money2(total or 0, where="balance.sum")

    def _transfer_sum(self, account_id: int, user_id: int, *, incoming: bool) -> Decimal:
        """Soma TRANSFER pagas com destino (incoming) ou origem (!incoming)."""
        side = (
            Transaction.destination_account_id == account_id
            if incoming
            else Transaction.account_id == account_id
        )
        total = (
            self.db.query(func.sum(Transaction.base_amount))
            .filter(
                Transaction.transaction_type == TransactionType.TRANSFER,
                Transaction.user_id == user_id,  # defense-in-depth (anti-IDOR)
                side,
                *_paid_filter(),
            )
            .scalar()
        )
        return to_money2(total or 0, where="balance.transfer")

    def get_total_balance(self, user_id: int) -> Decimal:
        """Patrimônio em contas = soma dos saldos das contas ativas do usuário.

        P0: moeda única (BRL). Contas em outra moeda entram sem conversão —
        conversão cambial é P1 (ver ADR-002). Investimentos não compõem
        (posição de carteira é relatório separado).
        """
        accounts = (
            self.db.query(Account)
            .filter(
                Account.user_id == user_id,
                Account.is_active.is_(True),
                Account.account_type != AccountType.CREDIT_CARD,
            )
            .all()
        )
        total = ZERO
        for acc in accounts:
            # Soft-deleted (is_deleted True) não compõem patrimônio.
            if getattr(acc, "is_deleted", False):
                continue
            total += self._compute(acc, user_id)
        return total.quantize(Decimal("0.01"))

    def recalculate_and_persist(
        self, account_id: int, user_id: int, *, commit: bool = False
    ) -> Decimal:
        """Recalcula e persiste `Account.balance` (único escritor)."""
        account = (
            self.db.query(Account)
            .filter(Account.id == account_id, Account.user_id == user_id)
            .first()
        )
        if not account:
            raise LookupError("Conta não encontrada para este usuário.")
        new_balance = self._compute(account, user_id)
        account.balance = new_balance
        self.db.flush()
        if commit:
            self.db.commit()
        return new_balance

    # ------------------------------------------------------------------
    # Resumos de período (KPIs — substituem as 4 definições divergentes)
    # ------------------------------------------------------------------
    def get_period_summary(
        self, user_id: int, start_date: date, end_date: date
    ) -> dict[str, Decimal]:
        """Receitas/despesas PAGAS (paid_date no período) + PENDENTES (due_date).

        TRANSFER excluído. Retorna Decimal (formatação na borda).
        """
        income_paid = self._period_sum(user_id, TransactionType.INCOME, True, start_date, end_date)
        expense_paid = self._period_sum(
            user_id, TransactionType.EXPENSE, True, start_date, end_date
        )
        income_pend = self._period_sum(user_id, TransactionType.INCOME, False, start_date, end_date)
        expense_pend = self._period_sum(
            user_id, TransactionType.EXPENSE, False, start_date, end_date
        )
        return {
            "income_paid": income_paid,
            "expense_paid": expense_paid,
            "balance_paid": (income_paid - expense_paid).quantize(Decimal("0.01")),
            "income_pending": income_pend,
            "expense_pending": expense_pend,
            "balance_forecast": (
                (income_paid + income_pend) - (expense_paid + expense_pend)
            ).quantize(Decimal("0.01")),
        }

    def _period_sum(
        self,
        user_id: int,
        type_: TransactionType,
        paid: bool,
        start_date: date,
        end_date: date,
    ) -> Decimal:
        query = self.db.query(func.sum(Transaction.base_amount)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == type_,
        )
        if paid:
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
        total = query.scalar()
        return to_money2(total or 0, where="balance.period")

    def reconcile(self, user_id: int) -> dict[str, object]:
        """Conciliação: calculado (transações) × persistido (Account.balance).

        Retorna divergências por conta. Vazio = consistente.
        """
        divergences = []
        accounts = self.db.query(Account).filter(Account.user_id == user_id).all()
        for acc in accounts:
            if getattr(acc, "is_deleted", False):
                continue
            computed = self._compute(acc, user_id)
            stored = to_money2(acc.balance or 0, where="balance.reconcile")
            if computed != stored:
                divergences.append(
                    {
                        "account_id": acc.id,
                        "account_name": acc.name,
                        "computed": str(computed),
                        "stored": str(stored),
                        "diff": str(computed - stored),
                    }
                )
        return {"ok": not divergences, "divergences": divergences}

    def touch_account(self, account_id: int | None, user_id: int) -> None:
        """Recalcula conta se pertencer ao usuário; silencioso se None/terceiro."""
        if account_id is None:
            return
        try:
            self.recalculate_and_persist(account_id, user_id)
        except LookupError:
            pass
