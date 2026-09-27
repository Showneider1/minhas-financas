"""
Serviço de transferências entre contas (P0 — ADR-002, Fase 5).

Modelagem: UMA linha `TRANSFER` (origem em `account_id`, destino em
`destination_account_id`, vinculadas por `transfer_group_id`). A "dualidade"
(débito origem / crédito destino) é calculada pelo BalanceService — não há
duas linhas contábeis.

Invariantes:
- Debita origem e credita destino (via BalanceService, mesma transação DB).
- NUNCA contabilizada como receita ou despesa (excluída de todos os sums).
- Patrimônio total inalterado pela transferência.
- Idempotente por `client_transfer_id` (UUID): retry idêntico retorna a linha
  original; retry com parâmetros DIVERGENTES levanta erro (anti-fraude).
- Auditável: log estruturado sem PII (ids + grupo + valor).
- Atômica: commit único; rollback em qualquer erro.
"""

import uuid
from datetime import date

from sqlalchemy.orm import Session

from config.logging_config import app_logger
from database.models.account import Account
from database.models.category import TransactionType
from database.models.transaction import Transaction, TransactionStatus
from services.balance_service import BalanceService
from utils.money import to_money2


class TransferError(ValueError):
    """Erro de regra de negócio em transferência."""


class TransferService:
    """Transferências idempotentes e auditáveis entre contas do mesmo usuário."""

    def __init__(self, db: Session):
        self.db = db
        self.balances = BalanceService(db)

    def transfer(
        self,
        user_id: int,
        from_account_id: int,
        to_account_id: int,
        amount,
        due_date: date | None = None,
        paid_date: date | None = None,
        description: str = "Transferência entre contas",
        category_id: int | None = None,
        client_transfer_id: str | None = None,
    ) -> Transaction:
        """Executa transferência. Retorna a linha TRANSFER (existente em retry)."""
        value = to_money2(amount, where="transfer.amount")
        if value <= 0:
            raise TransferError("Valor da transferência deve ser > 0.")
        if from_account_id == to_account_id:
            raise TransferError("Origem e destino devem ser contas diferentes.")

        origin = self._owned_account(user_id, from_account_id, "origem")
        dest = self._owned_account(user_id, to_account_id, "destino")

        # Categoria TRANSFER do próprio usuário (ou do sistema) — obrigatória
        # (Transaction.category_id é NOT NULL).
        if category_id is None:
            raise TransferError("Transferência exige categoria do tipo TRANSFER.")
        from database.models.category import Category

        cat = self.db.query(Category).filter(Category.id == category_id).first()
        if (
            not cat
            or cat.transaction_type != TransactionType.TRANSFER
            or (cat.user_id is not None and cat.user_id != user_id)
        ):
            raise TransferError(
                "Categoria da transferência deve ser TRANSFER e pertencer a este usuário."
            )

        # Idempotência: retry idêntico retorna a linha original; retry com
        # parâmetros divergentes é rejeitado (chave reutilizada indevidamente).
        if client_transfer_id:
            existing = (
                self.db.query(Transaction)
                .filter(
                    Transaction.client_transfer_id == client_transfer_id,
                    Transaction.user_id == user_id,
                )
                .first()
            )
            if existing:
                if (
                    existing.base_amount != value
                    or existing.account_id != origin.id
                    or existing.destination_account_id != dest.id
                ):
                    raise TransferError(
                        "Chave de idempotência reutilizada com parâmetros divergentes."
                    )
                app_logger.info(
                    f"Transferência idempotente: chave {client_transfer_id} "
                    f"já processada (tx {existing.id}) — sem duplicar."
                )
                return existing
        else:
            client_transfer_id = str(uuid.uuid4())

        group_id = str(uuid.uuid4())
        ref_date = due_date or date.today()
        is_paid = paid_date is not None

        try:
            tx = Transaction(
                user_id=user_id,
                description=(description or "Transferência entre contas")[:255],
                base_amount=value,
                transaction_type=TransactionType.TRANSFER,
                account_id=origin.id,
                destination_account_id=dest.id,
                category_id=category_id,
                purchase_date=ref_date,
                due_date=ref_date,
                paid_date=paid_date,
                status=TransactionStatus.PAID if is_paid else TransactionStatus.PENDING,
                transfer_group_id=group_id,
                client_transfer_id=client_transfer_id,
            )
            self.db.add(tx)
            self.db.flush()

            # Mesmo pendente, o vínculo existe; saldos movem quando paga.
            if is_paid:
                self.balances.recalculate_and_persist(origin.id, user_id)
                self.balances.recalculate_and_persist(dest.id, user_id)

            self.db.commit()
            self.db.refresh(tx)
        except Exception as exc:
            from sqlalchemy.exc import IntegrityError

            self.db.rollback()
            # Race: dois retries simultâneos com a mesma chave — um vence o
            # UNIQUE, o outro retorna a linha vencedora (idempotente).
            if isinstance(exc, IntegrityError) and client_transfer_id:
                winner = (
                    self.db.query(Transaction)
                    .filter(
                        Transaction.client_transfer_id == client_transfer_id,
                        Transaction.user_id == user_id,
                    )
                    .first()
                )
                if winner:
                    app_logger.info(
                        f"Transferência race resolvida pela chave {client_transfer_id} "
                        f"(tx {winner.id})."
                    )
                    return winner
            raise

        app_logger.info(
            f"Transferência {tx.id} (grupo {group_id}): conta {origin.id} -> "
            f"conta {dest.id}, valor {value}, usuário {user_id}"
        )
        return tx

    def confirm_transfer(
        self, transaction_id: int, user_id: int, paid_date: date | None = None
    ) -> Transaction:
        """Efetiva TRANSFER pendente (move saldos). Idempotente."""
        tx = self._owned_transfer(transaction_id, user_id)
        if tx.status == TransactionStatus.PAID and tx.paid_date is not None:
            return tx
        tx.paid_date = paid_date or date.today()
        tx.status = TransactionStatus.PAID
        try:
            self.balances.recalculate_and_persist(tx.account_id, user_id)
            if tx.destination_account_id:
                self.balances.recalculate_and_persist(tx.destination_account_id, user_id)
            self.db.commit()
            self.db.refresh(tx)
        except Exception:
            self.db.rollback()
            raise
        app_logger.info(f"Transferência {tx.id} efetivada (usuário {user_id})")
        return tx

    def _owned_account(self, user_id: int, account_id: int, papel: str) -> Account:
        acc = (
            self.db.query(Account)
            .filter(Account.id == account_id, Account.user_id == user_id)
            .first()
        )
        if not acc:
            raise TransferError(f"Conta de {papel} não encontrada para este usuário.")
        if not acc.is_active or getattr(acc, "is_deleted", False):
            raise TransferError(f"Conta de {papel} está inativa.")
        return acc

    def _owned_transfer(self, transaction_id: int, user_id: int) -> Transaction:
        tx = (
            self.db.query(Transaction)
            .filter(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id,
                Transaction.transaction_type == TransactionType.TRANSFER,
            )
            .first()
        )
        if not tx:
            raise TransferError("Transferência não encontrada para este usuário.")
        return tx

    @staticmethod
    def is_transfer(tx: Transaction) -> bool:
        return tx.transaction_type == TransactionType.TRANSFER
