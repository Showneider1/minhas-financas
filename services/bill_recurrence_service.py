"""Motor de recorrência de contas agendadas → transações (P1).

Gera, para um mês de competência, as `Transaction` PENDENTES correspondentes
às contas com `recurrence != NONE`, sem duplicar (idempotência por
`scheduled_bill_id` + mês/ano de competência do vencimento gerado).

Regras financeiras (fintech):
- Ocorrências ancoradas no `due_date` original: mensal = mesmo dia (travado no
  fim do mês: 31/01 → 28/02); semanal = +7 dias; trimestral +3 meses; anual +12.
- Dia útil ("fuzzy"): vencimento em sábado/domingo desloca para a próxima
  segunda-feira (convenção de cobrança BR). Feriados: fora do escopo P1
  (sem tabela de feriados — documentado).
- Competência = mês/ano do vencimento AJUSTADO.
- Contas `PAUSED`/`CANCELLED`/excluídas nunca geram; conta sem conta/categoria
  vinculada gera erro por item (não aborta o lote).
- Geração é por lote com relatório {generated, skipped, errors}; projeção
  (`project_period`) não persiste nada.
- Fuso: datas de conta são dias civis locais; usa `date.today()` do servidor
  (America/Sao_Paulo em produção — ver scheduler).
"""
from calendar import monthrange
from datetime import date, timedelta
from typing import Any, Dict, List

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from config.logging_config import app_logger
from database.enums import BillRecurrence, BillStatus, BillType, TransactionType
from database.models.scheduled_bill import ScheduledBill
from database.models.transaction import Transaction, TransactionStatus


def next_business_day(d: date) -> date:
    """Desloca sábado/domingo para a próxima segunda-feira (dia útil)."""
    if d.weekday() == 5:  # sábado
        return d + timedelta(days=2)
    if d.weekday() == 6:  # domingo
        return d + timedelta(days=1)
    return d


def clamp_day(year: int, month: int, day: int) -> date:
    """Data válida travando no fim do mês (31 → 28/29/30)."""
    last = monthrange(year, month)[1]
    return date(year, month, min(day, last))


def occurrences_in_month(bill: ScheduledBill, year: int, month: int) -> List[date]:
    """Vencimentos (ajustados p/ dia útil) da conta dentro do mês de competência."""
    if bill.recurrence == BillRecurrence.NONE:
        return []
    anchor = bill.due_date
    first_of_month = date(year, month, 1)
    last_day = monthrange(year, month)[1]
    last_of_month = date(year, month, last_day)
    found: List[date] = []

    if bill.recurrence == BillRecurrence.WEEKLY:
        # Avança de 7 em 7 dias a partir da âncora até cobrir o mês.
        cursor = anchor
        while cursor < first_of_month:
            cursor += timedelta(days=7)
        while cursor <= last_of_month:
            found.append(next_business_day(cursor))
            cursor += timedelta(days=7)
        return found

    step = {
        BillRecurrence.MONTHLY: relativedelta(months=1),
        BillRecurrence.QUARTERLY: relativedelta(months=3),
        BillRecurrence.YEARLY: relativedelta(years=1),
    }.get(bill.recurrence)
    if step is None:
        return []

    # Ancora mensal: mesmo dia (travado), avançando até alcançar o mês alvo.
    cursor = clamp_day(anchor.year, anchor.month, anchor.day)
    while (cursor.year, cursor.month) < (year, month):
        nxt = cursor + step
        cursor = clamp_day(nxt.year, nxt.month, anchor.day)
        if (cursor.year, cursor.month) > (year, month):
            return []
    if (cursor.year, cursor.month) == (year, month):
        found.append(next_business_day(cursor))
    return found


class BillRecurrenceService:
    """Geração idempotente de lançamentos a partir de contas recorrentes."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Seleção
    # ------------------------------------------------------------------
    def recurring_bills(self, user_id: int) -> List[ScheduledBill]:
        """Contas recorrentes elegíveis (dono, não pausadas/canceladas/excluídas)."""
        return (
            self.db.query(ScheduledBill)
            .filter(
                ScheduledBill.user_id == user_id,
                ScheduledBill.recurrence != BillRecurrence.NONE,
                ScheduledBill.is_paused.is_(False),
                ScheduledBill.status != BillStatus.CANCELLED,
                ScheduledBill.is_deleted.is_(False),
            )
            .order_by(ScheduledBill.due_date.asc())
            .all()
        )

    def _already_generated(self, bill_id: int, due: date) -> bool:
        """Idempotência exata: já existe lançamento desta conta p/ este vencimento?

        Compara a data AJUSTADA (dia útil) — se o ajuste empurrou o vencimento
        para o mês seguinte, a competência continua sendo o mês projetado e
        não há duplicata nem lacuna.
        """
        return (
            self.db.query(Transaction.id)
            .filter(
                Transaction.scheduled_bill_id == bill_id,
                Transaction.due_date == due,
            )
            .first()
            is not None
        )

    # ------------------------------------------------------------------
    # Projeção (sem persistir)
    # ------------------------------------------------------------------
    def project_period(
        self, user_id: int, year: int, month: int
    ) -> List[Dict[str, Any]]:
        """Prévia das ocorrências do mês (não persiste)."""
        preview = []
        for bill in self.recurring_bills(user_id):
            for due in occurrences_in_month(bill, year, month):
                preview.append(
                    {
                        "bill_id": bill.id,
                        "name": bill.name,
                        "bill_type": bill.bill_type.value,
                        "amount": str(bill.amount),
                        "due_date": due.isoformat(),
                        "already_generated": self._already_generated(bill.id, due),
                    }
                )
        return preview

    # ------------------------------------------------------------------
    # Geração (persiste, idempotente, com relatório por item)
    # ------------------------------------------------------------------
    def generate_period(
        self, user_id: int, year: int, month: int
    ) -> Dict[str, Any]:
        """Gera lançamentos PENDENTES da competência. Re-execução não duplica."""
        generated: List[int] = []
        skipped: List[int] = []
        errors: List[Dict[str, Any]] = []

        for bill in self.recurring_bills(user_id):
            for due in occurrences_in_month(bill, year, month):
                if self._already_generated(bill.id, due):
                    skipped.append(bill.id)
                    continue
                try:
                    tx = self._create_occurrence(bill, due)
                    generated.append(tx.id)
                except ValueError as exc:
                    errors.append({"bill_id": bill.id, "error": str(exc)})
                except Exception as exc:  # noqa: BLE001 — relatório por item
                    self.db.rollback()
                    errors.append({"bill_id": bill.id, "error": "falha interna"})
                    app_logger.error(f"Recorrência bill {bill.id}: {exc}")

        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        app_logger.info(
            f"Recorrência {month:02d}/{year} usuário {user_id}: "
            f"{len(generated)} gerados, {len(skipped)} ignorados, {len(errors)} erros"
        )
        return {"generated": generated, "skipped": skipped, "errors": errors}

    def _create_occurrence(self, bill: ScheduledBill, due: date) -> Transaction:
        if not bill.account_id or not bill.category_id:
            raise ValueError(
                f"Conta '{bill.name}' sem conta/categoria vinculada — "
                "vincule antes de gerar."
            )
        tx_type = (
            TransactionType.EXPENSE
            if bill.bill_type == BillType.PAYABLE
            else TransactionType.INCOME
        )
        from database.models.category import Category

        cat = self.db.query(Category).filter(Category.id == bill.category_id).first()
        if cat and cat.transaction_type is not None and cat.transaction_type != tx_type:
            raise ValueError(
                f"Conta '{bill.name}': categoria incompatível com o tipo."
            )
        tx = Transaction(
            user_id=bill.user_id,
            description=f"{bill.name} (recorrente {due.month:02d}/{due.year})",
            base_amount=bill.amount,
            transaction_type=tx_type,
            account_id=bill.account_id,
            category_id=bill.category_id,
            purchase_date=due,
            due_date=due,
            paid_date=None,
            status=TransactionStatus.PENDING,
            scheduled_bill_id=bill.id,
            notes=f"gerado de scheduled_bill:{bill.id}",
        )
        self.db.add(tx)
        self.db.flush()
        return tx

    # ------------------------------------------------------------------
    # Pausa / retomada
    # ------------------------------------------------------------------
    def set_paused(self, bill_id: int, user_id: int, paused: bool) -> ScheduledBill:
        """Pausa/retoma conta recorrente (dono)."""
        bill = (
            self.db.query(ScheduledBill)
            .filter(
                ScheduledBill.id == bill_id,
                ScheduledBill.user_id == user_id,
                ScheduledBill.is_deleted.is_(False),
            )
            .first()
        )
        if not bill:
            raise ValueError("Conta não encontrada para este usuário.")
        bill.is_paused = paused
        self.db.commit()
        self.db.refresh(bill)
        return bill
