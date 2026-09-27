"""Motor de recorrência de contas agendadas (Missão P1 Fases 3/4).

Cobre: geração mensal na competência, anti-duplicidade em re-execução,
dia útil (fim de semana → segunda), trava de fim de mês, pausa,
conta sem vínculo (erro por item) e projeção sem persistir.
"""
from datetime import date
from decimal import Decimal

from database.enums import BillRecurrence, BillStatus, BillType, TransactionType
from database.models.transaction import Transaction, TransactionStatus
from services.bill_recurrence_service import (
    BillRecurrenceService,
    clamp_day,
    next_business_day,
    occurrences_in_month,
)
from services.scheduled_bill_service import ScheduledBillService


def _bill(db, user, account, category, name="Aluguel", amount="1500.00",
          due=date(2026, 1, 10), bill_type=BillType.PAYABLE,
          recurrence=BillRecurrence.MONTHLY):
    return ScheduledBillService(db).create_bill(
        user_id=user.id, name=name, amount=Decimal(amount), bill_type=bill_type,
        due_date=due, account_id=account.id if account else None,
        category_id=category.id if category else None, recurrence=recurrence,
    )


def test_next_business_day_weekend():
    assert next_business_day(date(2026, 8, 1)) == date(2026, 8, 3)  # sáb → seg
    assert next_business_day(date(2026, 8, 2)) == date(2026, 8, 3)  # dom → seg
    assert next_business_day(date(2026, 8, 5)) == date(2026, 8, 5)  # qua


def test_clamp_month_end():
    assert clamp_day(2026, 2, 31) == date(2026, 2, 28)
    assert clamp_day(2026, 4, 31) == date(2026, 4, 30)


def test_monthly_generation_in_competence(db, sample_user, sample_account, sample_category):
    svc = BillRecurrenceService(db)
    bill = _bill(db, sample_user, sample_account, sample_category)
    report = svc.generate_period(sample_user.id, 2026, 3)
    assert report["errors"] == []
    assert len(report["generated"]) == 1

    tx = db.query(Transaction).filter(
        Transaction.scheduled_bill_id == bill.id).first()
    assert tx is not None
    assert tx.base_amount == Decimal("1500.00")
    assert tx.transaction_type == TransactionType.EXPENSE
    assert tx.status == TransactionStatus.PENDING
    assert tx.paid_date is None
    assert tx.due_date == date(2026, 3, 10)


def test_double_run_no_duplicates(db, sample_user, sample_account, sample_category):
    svc = BillRecurrenceService(db)
    _bill(db, sample_user, sample_account, sample_category)
    first = svc.generate_period(sample_user.id, 2026, 3)
    second = svc.generate_period(sample_user.id, 2026, 3)
    assert len(first["generated"]) == 1
    assert second["generated"] == []
    assert len(second["skipped"]) == 1
    assert db.query(Transaction).filter(
        Transaction.user_id == sample_user.id).count() == 1


def test_weekend_shifts_to_monday(db, sample_user, sample_account, sample_category):
    svc = BillRecurrenceService(db)
    # Âncora 04/07/2026 (sábado) → ocorrência de julho desloca p/ 06/07 (seg).
    _bill(db, sample_user, sample_account, sample_category, due=date(2026, 7, 4))
    report = svc.generate_period(sample_user.id, 2026, 7)
    assert len(report["generated"]) == 1
    tx = db.query(Transaction).filter(
        Transaction.user_id == sample_user.id).first()
    assert tx.due_date == date(2026, 7, 6)
    # Re-execução não duplica mesmo com deslocamento de mês.
    again = svc.generate_period(sample_user.id, 2026, 7)
    assert again["generated"] == []


def test_month_end_clamp(db, sample_user, sample_account, sample_category):
    svc = BillRecurrenceService(db)
    _bill(db, sample_user, sample_account, sample_category, due=date(2026, 1, 31))
    report = svc.generate_period(sample_user.id, 2026, 2)
    assert len(report["generated"]) == 1
    tx = db.query(Transaction).filter(
        Transaction.user_id == sample_user.id).first()
    # 28/02/2026 é sábado → dia útil 02/03, sem duplicar nem perder.
    assert tx.due_date == date(2026, 3, 2)


def test_paused_bill_skipped(db, sample_user, sample_account, sample_category):
    svc = BillRecurrenceService(db)
    bill = _bill(db, sample_user, sample_account, sample_category)
    svc.set_paused(bill.id, sample_user.id, True)
    report = svc.generate_period(sample_user.id, 2026, 3)
    assert report["generated"] == []
    svc.set_paused(bill.id, sample_user.id, False)
    report = svc.generate_period(sample_user.id, 2026, 3)
    assert len(report["generated"]) == 1


def test_bill_without_links_reports_error(db, sample_user):
    svc = BillRecurrenceService(db)
    _bill(db, sample_user, None, None)
    report = svc.generate_period(sample_user.id, 2026, 3)
    assert report["generated"] == []
    assert len(report["errors"]) == 1
    assert db.query(Transaction).filter(
        Transaction.user_id == sample_user.id).count() == 0


def test_cancelled_and_deleted_never_generate(
    db, sample_user, sample_account, sample_category
):
    svc = BillRecurrenceService(db)
    billsvc = ScheduledBillService(db)
    bill = _bill(db, sample_user, sample_account, sample_category)
    bill.status = BillStatus.CANCELLED
    db.commit()
    assert svc.generate_period(sample_user.id, 2026, 3)["generated"] == []
    bill.status = BillStatus.PENDING
    billsvc.delete_bill(bill.id, sample_user.id)
    assert svc.generate_period(sample_user.id, 2026, 3)["generated"] == []


def test_project_does_not_persist(db, sample_user, sample_account, sample_category):
    svc = BillRecurrenceService(db)
    _bill(db, sample_user, sample_account, sample_category)
    preview = svc.project_period(sample_user.id, 2026, 3)
    assert len(preview) == 1
    assert preview[0]["due_date"] == "2026-03-10"
    assert preview[0]["already_generated"] is False
    assert db.query(Transaction).filter(
        Transaction.user_id == sample_user.id).count() == 0
    svc.generate_period(sample_user.id, 2026, 3)
    assert svc.project_period(sample_user.id, 2026, 3)[0]["already_generated"] is True


def test_weekly_multiple_occurrences(db, sample_user, sample_account, sample_category):
    svc = BillRecurrenceService(db)
    _bill(db, sample_user, sample_account, sample_category, name="Faxina",
          amount="120.00", due=date(2026, 3, 2),
          recurrence=BillRecurrence.WEEKLY)
    report = svc.generate_period(sample_user.id, 2026, 3)
    # Segundas de março/2026: 2, 9, 16, 23, 30 → 5 ocorrências.
    assert len(report["generated"]) == 5


def test_occurrences_quarterly_yearly_anchors(db, sample_user, sample_account, sample_category):
    bill = _bill(db, sample_user, sample_account, sample_category,
                 due=date(2026, 1, 15), recurrence=BillRecurrence.QUARTERLY)
    assert [d.isoformat() for d in occurrences_in_month(bill, 2026, 4)] == ["2026-04-15"]
    assert occurrences_in_month(bill, 2026, 2) == []
    bill.recurrence = BillRecurrence.YEARLY
    assert [d.isoformat() for d in occurrences_in_month(bill, 2027, 1)] == ["2027-01-15"]
    assert occurrences_in_month(bill, 2026, 6) == []


def test_receivable_generates_income(db, sample_user, sample_account):
    from database.models.category import Category

    cat = Category(user_id=sample_user.id, name="Salário",
                   transaction_type=TransactionType.INCOME, is_system=False)
    db.add(cat)
    db.commit()
    svc = BillRecurrenceService(db)
    _bill(db, sample_user, sample_account, cat, name="Salário",
          amount="5000.00", bill_type=BillType.RECEIVABLE)
    svc.generate_period(sample_user.id, 2026, 3)
    tx = db.query(Transaction).filter(
        Transaction.user_id == sample_user.id).first()
    assert tx.transaction_type == TransactionType.INCOME
