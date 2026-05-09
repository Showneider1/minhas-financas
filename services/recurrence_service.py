"""
Serviço de Recorrência e Parcelamento.

Responsável por gerar automaticamente as transações filhas a partir
de uma transação-base marcada como is_recurring ou com total_installments > 1.

Não altera nenhum arquivo existente: consome Transaction/TransactionStatus
jeá definidos em database/models/transaction.py e usa a Session diretamente.

Uso típico:
    service = RecurrenceService(db)

    # Parcelamento: gera as N parcelas de uma vez
    parcelas = service.generate_installments(transaction_base, total=6)

    # Recorrência mensal: gera a próxima ocorrência no mês seguinte
    proxima = service.generate_next_recurring(transaction_recorrente)

    # Checagem automática: quais recorrências do usuário precisam ser geradas?
    pendentes = service.get_pending_recurrences(user_id, target_month, target_year)
"""
from __future__ import annotations

import math
from datetime import date
from dateutil.relativedelta import relativedelta
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import extract, and_

from database.models.transaction import Transaction, TransactionStatus
from database.models.category import TransactionType
from config.logging_config import app_logger


class RecurrenceService:
    """
    Serviço de geração automática de parcelas e recorrências mensais.
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # PÚblica: Parcelamento
    # ------------------------------------------------------------------

    def generate_installments(
        self,
        base_transaction: Transaction,
        total: int,
    ) -> List[Transaction]:
        """
        Gera `total` parcelas a partir de uma transação-base.

        A transação-base se torna a parcela 1/N.
        As demais são criadas com due_date avançando um mês por parcela.
        Todas iniciam com status PENDING e paid_date=None.

        Args:
            base_transaction: Transação já persistida que serve de template.
            total: Número total de parcelas (deve ser >= 2).

        Returns:
            Lista das transações geradas (sem a base_transaction).
        """
        if total < 2:
            raise ValueError("total de parcelas deve ser >= 2")

        # Atualiza a base como parcela 1/N
        base_transaction.installment_number = 1
        base_transaction.total_installments = total
        base_transaction.is_recurring = False  # parcelado ≠ recorrente
        self.db.flush()

        generated: List[Transaction] = []

        for i in range(2, total + 1):
            due = self._advance_months(base_transaction.due_date, i - 1)
            purchase = self._advance_months(base_transaction.purchase_date, i - 1)

            installment = Transaction(
                user_id=base_transaction.user_id,
                description=base_transaction.description,
                base_amount=base_transaction.base_amount,
                transaction_type=base_transaction.transaction_type,
                category_id=base_transaction.category_id,
                account_id=base_transaction.account_id,
                purchase_date=purchase,
                due_date=due,
                paid_date=None,
                status=TransactionStatus.PENDING,
                is_recurring=False,
                installment_number=i,
                total_installments=total,
                notes=base_transaction.notes,
            )
            self.db.add(installment)
            generated.append(installment)

        self.db.commit()
        for t in generated:
            self.db.refresh(t)

        app_logger.info(
            f"Parcelamento gerado: transação {base_transaction.id} "
            f"→ {total} parcelas (user {base_transaction.user_id})"
        )
        return generated

    # ------------------------------------------------------------------
    # PÚblica: Recorrência Mensal
    # ------------------------------------------------------------------

    def generate_next_recurring(
        self,
        transaction: Transaction,
    ) -> Optional[Transaction]:
        """
        Gera a próxima ocorrência mensal de uma transação recorrente.

        Verifica se já existe uma transação para o mês seguinte com
        a mesma descrição e categoria antes de criar, garantindo
        idempotência (seguro chamar múltiplas vezes).

        Returns:
            Nova Transaction gerada, ou None se já existia.
        """
        if not transaction.is_recurring:
            raise ValueError("Transação não marcada como recorrente")

        next_due = self._advance_months(transaction.due_date, 1)
        next_purchase = self._advance_months(transaction.purchase_date, 1)

        # Idempotência: evita duplicatas
        exists = self._find_existing(
            user_id=transaction.user_id,
            description=transaction.description,
            category_id=transaction.category_id,
            month=next_due.month,
            year=next_due.year,
        )
        if exists:
            app_logger.debug(
                f"Recorrência já existe para '{transaction.description}' "
                f"em {next_due.month}/{next_due.year} — ignorando."
            )
            return None

        next_occurrence = Transaction(
            user_id=transaction.user_id,
            description=transaction.description,
            base_amount=transaction.base_amount,
            transaction_type=transaction.transaction_type,
            category_id=transaction.category_id,
            account_id=transaction.account_id,
            purchase_date=next_purchase,
            due_date=next_due,
            paid_date=None,
            status=TransactionStatus.PENDING,
            is_recurring=True,
            installment_number=1,
            total_installments=1,
            notes=transaction.notes,
        )
        self.db.add(next_occurrence)
        self.db.commit()
        self.db.refresh(next_occurrence)

        app_logger.info(
            f"Recorrência gerada: '{transaction.description}' "
            f"→ {next_due.month}/{next_due.year} (user {transaction.user_id})"
        )
        return next_occurrence

    # ------------------------------------------------------------------
    # PÚblica: Checagem em Lote (ex: chamada mensal via scheduler)
    # ------------------------------------------------------------------

    def get_pending_recurrences(
        self,
        user_id: int,
        target_month: int,
        target_year: int,
    ) -> List[Transaction]:
        """
        Retorna todas as transações recorrentes do usuário cujo
        mês seguinte (target_month/target_year) ainda não foi gerado.

        útil para implementar um job mensal automático que percorre
        todos os usuários e gera as recorrências pendentes.
        """
        # Mês anterior ao alvo (onde as recorrências-fonte vivem)
        if target_month == 1:
            source_month, source_year = 12, target_year - 1
        else:
            source_month, source_year = target_month - 1, target_year

        # Recorrências do mês anterior
        sources = (
            self.db.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.is_recurring == True,
                extract("month", Transaction.due_date) == source_month,
                extract("year",  Transaction.due_date) == source_year,
            )
            .all()
        )

        pending = []
        for src in sources:
            exists = self._find_existing(
                user_id=user_id,
                description=src.description,
                category_id=src.category_id,
                month=target_month,
                year=target_year,
            )
            if not exists:
                pending.append(src)

        return pending

    def process_all_pending_recurrences(
        self,
        user_id: int,
        target_month: int,
        target_year: int,
    ) -> int:
        """
        Gera automaticamente todas as recorrências pendentes para o mês alvo.

        Returns:
            Número de novas transações criadas.
        """
        pending = self.get_pending_recurrences(user_id, target_month, target_year)
        count = 0
        for src in pending:
            result = self.generate_next_recurring(src)
            if result:
                count += 1
        return count

    # ------------------------------------------------------------------
    # Privado
    # ------------------------------------------------------------------

    @staticmethod
    def _advance_months(d: date, months: int) -> date:
        """Avança uma data por N meses preservando o dia (ou fim do mês)."""
        return d + relativedelta(months=months)

    def _find_existing(
        self,
        user_id: int,
        description: str,
        category_id: int,
        month: int,
        year: int,
    ) -> Optional[Transaction]:
        """Verifica se já existe uma transação com mesma descrição/categoria no período."""
        return (
            self.db.query(Transaction)
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.description == description,
                    Transaction.category_id == category_id,
                    extract("month", Transaction.due_date) == month,
                    extract("year",  Transaction.due_date) == year,
                )
            )
            .first()
        )
