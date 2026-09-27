"""Servico de Contas a Pagar e a Receber (ScheduledBill) — P0 (ADR-002).

- Valores Decimal (Numeric).
- Pagar conta GERA o Transaction correspondente (rastreabilidade + fluxo de
  caixa corretos). Idempotente via `scheduled_bill_id` (sem duplicar em retry).
- Isolamento por user_id em todos os métodos.
"""
from datetime import datetime, timezone, date, timedelta
from dateutil.relativedelta import relativedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_

from database.models.scheduled_bill import ScheduledBill, BillType, BillStatus, BillRecurrence
from config.logging_config import app_logger
from utils.money import to_money2, money_sum


class ScheduledBillService:
    """CRUD e logica de negocio para Contas a Pagar/Receber.

    Responsabilidades:
    - Criar, editar, excluir e listar contas
    - Marcar como pagas com valor e data efetiva
    - Detectar contas vencidas e atualizar status automaticamente
    - Gerar proxima parcela para contas recorrentes
    - Emitir alertas de vencimento proximo
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ #
    # CRUD                                                                  #
    # ------------------------------------------------------------------ #

    def create_bill(
        self,
        user_id: int,
        name: str,
        amount,
        bill_type: BillType,
        due_date: date,
        account_id: Optional[int] = None,
        category_id: Optional[int] = None,
        description: Optional[str] = None,
        recurrence: BillRecurrence = BillRecurrence.NONE,
        reminder_days_before: int = 3,
        notes: Optional[str] = None,
    ) -> ScheduledBill:
        """Cria uma nova conta a pagar ou receber.

        Args:
            user_id: ID do usuario
            name: Nome da conta (ex: 'Aluguel', 'Salario')
            amount: Valor da conta (Decimal/str/int — nunca float)
            bill_type: PAYABLE ou RECEIVABLE
            due_date: Data de vencimento
            account_id: Conta bancaria vinculada
            category_id: Categoria da despesa/receita
            description: Descricao adicional
            recurrence: Frequencia de repeticao
            reminder_days_before: Dias de antecedencia para alerta
            notes: Observacoes livres

        Returns:
            ScheduledBill criada e persistida

        Raises:
            ValueError: Se amount <= 0 ou reminder_days_before < 0
        """
        value = to_money2(amount, where="bill.create")
        if value <= 0:
            raise ValueError("O valor da conta deve ser maior que zero.")
        if reminder_days_before < 0:
            raise ValueError("Os dias de lembrete nao podem ser negativos.")
        # P0 (IDOR): conta/categoria vinculadas devem ser do usuário.
        if account_id is not None:
            from database.models.account import Account

            owned = (
                self.db.query(Account.id)
                .filter(Account.id == account_id, Account.user_id == user_id)
                .first()
            )
            if not owned:
                raise ValueError("Conta vinculada não pertence a este usuário.")
        if category_id is not None:
            from database.models.category import Category

            cat = self.db.query(Category).filter(Category.id == category_id).first()
            if not cat or (cat.user_id is not None and cat.user_id != user_id):
                raise ValueError("Categoria vinculada não pertence a este usuário.")

        bill = ScheduledBill(
            user_id=user_id,
            name=name,
            amount=value,
            bill_type=bill_type,
            due_date=due_date,
            account_id=account_id,
            category_id=category_id,
            description=description,
            recurrence=recurrence,
            reminder_days_before=reminder_days_before,
            notes=notes,
            status=BillStatus.PENDING,
        )
        self.db.add(bill)
        self.db.commit()
        self.db.refresh(bill)
        app_logger.info(
            f"Conta criada: id={bill.id} user_id={user_id} "
            f"nome='{name}' tipo={bill_type.value} venc={due_date}"
        )
        return bill

    def get_bill(self, bill_id: int, user_id: int) -> Optional[ScheduledBill]:
        """Retorna uma conta pelo ID garantindo pertencer ao usuario."""
        return (
            self.db.query(ScheduledBill)
            .filter(
                and_(
                    ScheduledBill.id == bill_id,
                    ScheduledBill.user_id == user_id,
                    ScheduledBill.is_deleted.is_(False),
                )
            )
            .first()
        )

    def list_bills(
        self,
        user_id: int,
        bill_type: Optional[BillType] = None,
        status: Optional[BillStatus] = None,
        due_from: Optional[date] = None,
        due_to: Optional[date] = None,
    ) -> List[ScheduledBill]:
        """Lista contas do usuario com filtros opcionais."""
        query = self.db.query(ScheduledBill).filter(
            and_(
                ScheduledBill.user_id == user_id,
                ScheduledBill.is_deleted.is_(False),
            )
        )
        if bill_type:
            query = query.filter(ScheduledBill.bill_type == bill_type)
        if status:
            query = query.filter(ScheduledBill.status == status)
        if due_from:
            query = query.filter(ScheduledBill.due_date >= due_from)
        if due_to:
            query = query.filter(ScheduledBill.due_date <= due_to)
        return query.order_by(ScheduledBill.due_date.asc()).all()

    def mark_as_paid(
        self,
        bill_id: int,
        user_id: int,
        paid_amount=None,
        paid_date: Optional[date] = None,
    ) -> Optional[ScheduledBill]:
        """Marca conta como paga/recebida e GERA o Transaction correspondente.

        Geração do lançamento (P0 — rastreabilidade):
        - PAYABLE -> EXPENSE paga; RECEIVABLE -> INCOME pago.
        - Vinculado via `scheduled_bill_id`; idempotente (não duplica em retry).
        - Exige conta e categoria vinculadas (sem elas não há onde lançar).
        - Move o saldo via FinanceService (mesmo commit).

        Args:
            bill_id: ID da conta
            user_id: ID do usuario
            paid_amount: Valor efetivo (Decimal/str/int; nominal se None;
                deve ser > 0)
            paid_date: Data do pagamento (hoje se None)

        Returns:
            Conta atualizada; None se nao encontrada
        """
        bill = self.get_bill(bill_id, user_id)
        if not bill:
            return None
        if bill.status == BillStatus.CANCELLED:
            raise ValueError("Conta cancelada não pode ser paga.")
        if bill.status == BillStatus.PAID:
            self._ensure_transaction(bill)
            return bill  # Idempotente

        effective = (
            to_money2(paid_amount, where="bill.pay")
            if paid_amount is not None
            else to_money2(bill.amount, where="bill.pay")
        )
        if effective <= 0:
            raise ValueError("O valor pago deve ser maior que zero.")

        bill.status = BillStatus.PAID
        bill.paid_amount = effective
        bill.paid_date = paid_date or date.today()
        bill.updated_at = datetime.now(timezone.utc)
        try:
            self.db.flush()
            self._ensure_transaction(bill)
            self.db.commit()
            self.db.refresh(bill)
        except Exception:
            self.db.rollback()
            raise

        app_logger.info(
            f"Conta paga: id={bill_id} valor={effective:.2f} data={bill.paid_date}"
        )

        # Se recorrente, gera proxima parcela automaticamente
        if bill.recurrence != BillRecurrence.NONE:
            self._generate_next_recurrence(bill)

        return bill

    def _ensure_transaction(self, bill: ScheduledBill):
        """Cria o Transaction do pagamento (se ainda não existir)."""
        from database.models.transaction import Transaction, TransactionStatus
        from database.models.category import TransactionType

        existing = (
            self.db.query(Transaction.id)
            .filter(Transaction.scheduled_bill_id == bill.id)
            .first()
        )
        if existing:
            return existing

        if not bill.account_id or not bill.category_id:
            raise ValueError(
                "Conta agendada sem conta/categoria vinculada — "
                "vincule antes de pagar para gerar o lançamento."
            )
        tx_type = (
            TransactionType.EXPENSE
            if bill.bill_type == BillType.PAYABLE
            else TransactionType.INCOME
        )
        tx = Transaction(
            user_id=bill.user_id,
            description=f"{bill.name} (conta agendada)",
            base_amount=to_money2(bill.paid_amount or bill.amount, where="bill.tx"),
            transaction_type=tx_type,
            account_id=bill.account_id,
            category_id=bill.category_id,
            purchase_date=bill.paid_date or bill.due_date,
            due_date=bill.due_date,
            paid_date=bill.paid_date or date.today(),
            status=TransactionStatus.PAID,
            scheduled_bill_id=bill.id,
            notes=bill.notes,
        )
        self.db.add(tx)
        self.db.flush()

        from services.balance_service import BalanceService

        BalanceService(self.db).recalculate_and_persist(bill.account_id, bill.user_id)
        return tx

    def delete_bill(self, bill_id: int, user_id: int) -> bool:
        """Soft-delete de uma conta.

        NOTA: o Transaction já gerado pelo pagamento é preservado
        (histórico/auditoria). Estorno é operação separada e explícita.
        """
        bill = self.get_bill(bill_id, user_id)
        if not bill:
            return False
        bill.is_deleted = True
        bill.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        return True

    # ------------------------------------------------------------------ #
    # OVERDUE DETECTION                                                     #
    # ------------------------------------------------------------------ #

    def update_overdue_bills(self, user_id: int) -> int:
        """Atualiza status para OVERDUE em contas vencidas nao pagas.

        Deve ser chamado pelo background job diariamente.

        Returns:
            Numero de contas atualizadas para OVERDUE
        """
        today = date.today()
        overdue_bills = (
            self.db.query(ScheduledBill)
            .filter(
                and_(
                    ScheduledBill.user_id == user_id,
                    ScheduledBill.status == BillStatus.PENDING,
                    ScheduledBill.due_date < today,
                    ScheduledBill.is_deleted.is_(False),
                )
            )
            .all()
        )
        for bill in overdue_bills:
            bill.status = BillStatus.OVERDUE
            bill.updated_at = datetime.now(timezone.utc)

        if overdue_bills:
            self.db.commit()
            app_logger.info(
                f"Contas marcadas como vencidas: user_id={user_id} total={len(overdue_bills)}"
            )
        return len(overdue_bills)

    # ------------------------------------------------------------------ #
    # ALERTS & UPCOMING                                                     #
    # ------------------------------------------------------------------ #

    def get_upcoming_bills(
        self,
        user_id: int,
        days_ahead: int = 30,
    ) -> Dict[str, Any]:
        """Retorna contas proximas do vencimento para o dashboard.

        Args:
            user_id: ID do usuario
            days_ahead: Quantos dias a frente verificar (padrao: 30)

        Returns:
            Dict com:
            - overdue: contas ja vencidas (nao pagas)
            - due_today: vencem hoje
            - due_this_week: vencem em 7 dias
            - due_this_month: vencem em 30 dias
            - total_payable: soma total a pagar no periodo
            - total_receivable: soma total a receber no periodo
        """
        today = date.today()
        future_limit = today + timedelta(days=days_ahead)

        # Contas vencidas
        overdue = self.list_bills(
            user_id, status=BillStatus.OVERDUE,
        )

        # Contas a vencer no periodo
        upcoming = self.list_bills(
            user_id,
            status=BillStatus.PENDING,
            due_from=today,
            due_to=future_limit,
        )

        due_today = [b for b in upcoming if b.due_date == today]
        due_this_week = [b for b in upcoming if b.due_date <= today + timedelta(days=7)]

        total_payable = money_sum(
            b.amount for b in upcoming + overdue
            if b.bill_type == BillType.PAYABLE
        )
        # P0: RECEIVABLE vencido também compõe o a receber (antes era ignorado).
        total_receivable = money_sum(
            b.amount for b in upcoming + overdue
            if b.bill_type == BillType.RECEIVABLE
        )

        def _serialize(bill: ScheduledBill) -> dict:
            return {
                "id": bill.id,
                "name": bill.name,
                "amount": bill.amount,
                "type": bill.bill_type.value,
                "due_date": bill.due_date.isoformat(),
                "days_until_due": bill.days_until_due,
                "status": bill.status.value,
                "recurrence": bill.recurrence.value,
            }

        return {
            "overdue": [_serialize(b) for b in overdue],
            "due_today": [_serialize(b) for b in due_today],
            "due_this_week": [_serialize(b) for b in due_this_week],
            "due_this_month": [_serialize(b) for b in upcoming],
            "total_payable": total_payable,
            "total_receivable": total_receivable,
            "net_cash_flow": total_receivable - total_payable,
        }

    # ------------------------------------------------------------------ #
    # RECURRENCE GENERATION                                                 #
    # ------------------------------------------------------------------ #

    def _generate_next_recurrence(self, paid_bill: ScheduledBill) -> Optional[ScheduledBill]:
        """Gera a proxima parcela de uma conta recorrente apos pagamento.

        Calcula a proxima data de vencimento baseada na frequencia.
        """
        if paid_bill.recurrence == BillRecurrence.NONE:
            return None

        delta_map = {
            BillRecurrence.WEEKLY:    timedelta(weeks=1),
            BillRecurrence.MONTHLY:   relativedelta(months=1),
            BillRecurrence.QUARTERLY: relativedelta(months=3),
            BillRecurrence.YEARLY:    relativedelta(years=1),
        }
        delta = delta_map.get(paid_bill.recurrence)
        if not delta:
            return None

        next_due = paid_bill.due_date + delta

        next_bill = ScheduledBill(
            user_id=paid_bill.user_id,
            account_id=paid_bill.account_id,
            category_id=paid_bill.category_id,
            name=paid_bill.name,
            description=paid_bill.description,
            bill_type=paid_bill.bill_type,
            amount=paid_bill.amount,
            due_date=next_due,
            status=BillStatus.PENDING,
            recurrence=paid_bill.recurrence,
            reminder_days_before=paid_bill.reminder_days_before,
            parent_bill_id=paid_bill.id,
            notes=paid_bill.notes,
        )
        self.db.add(next_bill)
        self.db.commit()
        self.db.refresh(next_bill)
        app_logger.info(
            f"Proxima recorrencia gerada: parent_id={paid_bill.id} "
            f"id={next_bill.id} venc={next_due}"
        )
        return next_bill
