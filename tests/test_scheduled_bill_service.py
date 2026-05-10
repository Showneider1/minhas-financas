import pytest
from decimal import Decimal
from datetime import date, timedelta
from database.models import ScheduledBill, BillStatus, BillType, BillRecurrence
from services.scheduled_bill_service import ScheduledBillService


class TestScheduledBillService:

    def test_create_scheduled_bill(self, db, sample_user, sample_account, sample_category):
        bill = ScheduledBillService.create_scheduled_bill(
            db=db,
            user_id=sample_user.id,
            account_id=sample_account.id,
            category_id=sample_category.id,
            name="Aluguel",
            amount=Decimal("1500.00"),
            due_date=date.today() + timedelta(days=5),
            bill_type=BillType.EXPENSE,
            recurrence=BillRecurrence.MONTHLY,
        )
        assert bill.id is not None
        assert bill.name == "Aluguel"
        assert bill.amount == Decimal("1500.00")
        assert bill.status == BillStatus.PENDING

    def test_mark_bill_as_paid(self, db, sample_user, sample_account, sample_category):
        bill = ScheduledBillService.create_scheduled_bill(
            db=db,
            user_id=sample_user.id,
            account_id=sample_account.id,
            category_id=sample_category.id,
            name="Internet",
            amount=Decimal("120.00"),
            due_date=date.today() + timedelta(days=3),
            bill_type=BillType.EXPENSE,
        )
        paid = ScheduledBillService.mark_as_paid(
            db=db, bill_id=bill.id, paid_date=date.today()
        )
        assert paid.status == BillStatus.PAID
        assert paid.paid_date == date.today()

    def test_get_pending_bills_by_user(self, db, sample_user, sample_account, sample_category):
        ScheduledBillService.create_scheduled_bill(
            db=db,
            user_id=sample_user.id,
            account_id=sample_account.id,
            category_id=sample_category.id,
            name="Agua",
            amount=Decimal("80.00"),
            due_date=date.today() + timedelta(days=2),
            bill_type=BillType.EXPENSE,
        )
        pending = ScheduledBillService.get_pending_bills(
            db=db, user_id=sample_user.id
        )
        assert len(pending) >= 1

    def test_get_overdue_bills(self, db, sample_user, sample_account, sample_category):
        ScheduledBillService.create_scheduled_bill(
            db=db,
            user_id=sample_user.id,
            account_id=sample_account.id,
            category_id=sample_category.id,
            name="Conta Vencida",
            amount=Decimal("200.00"),
            due_date=date.today() - timedelta(days=5),
            bill_type=BillType.EXPENSE,
        )
        overdue = ScheduledBillService.get_overdue_bills(
            db=db, user_id=sample_user.id
        )
        assert len(overdue) >= 1

    def test_get_bills_due_soon(self, db, sample_user, sample_account, sample_category):
        ScheduledBillService.create_scheduled_bill(
            db=db,
            user_id=sample_user.id,
            account_id=sample_account.id,
            category_id=sample_category.id,
            name="Energia",
            amount=Decimal("300.00"),
            due_date=date.today() + timedelta(days=4),
            bill_type=BillType.EXPENSE,
        )
        due_soon = ScheduledBillService.get_bills_due_soon(
            db=db, user_id=sample_user.id, days_ahead=7
        )
        assert len(due_soon) >= 1

    def test_delete_bill(self, db, sample_user, sample_account, sample_category):
        bill = ScheduledBillService.create_scheduled_bill(
            db=db,
            user_id=sample_user.id,
            account_id=sample_account.id,
            category_id=sample_category.id,
            name="Assinatura Temp",
            amount=Decimal("50.00"),
            due_date=date.today() + timedelta(days=10),
            bill_type=BillType.EXPENSE,
        )
        bill_id = bill.id
        ScheduledBillService.delete_bill(db=db, bill_id=bill_id)
        deleted = db.query(ScheduledBill).filter(ScheduledBill.id == bill_id).first()
        assert deleted is None

    def test_get_bills_summary(self, db, sample_user, sample_account, sample_category):
        ScheduledBillService.create_scheduled_bill(
            db=db,
            user_id=sample_user.id,
            account_id=sample_account.id,
            category_id=sample_category.id,
            name="Salario",
            amount=Decimal("5000.00"),
            due_date=date.today() + timedelta(days=1),
            bill_type=BillType.INCOME,
            recurrence=BillRecurrence.MONTHLY,
        )
        summary = ScheduledBillService.get_bills_summary(
            db=db, user_id=sample_user.id
        )
        assert "total_pending" in summary
        assert "total_amount_pending" in summary

    def test_create_next_recurrence(self, db, sample_user, sample_account, sample_category):
        bill = ScheduledBillService.create_scheduled_bill(
            db=db,
            user_id=sample_user.id,
            account_id=sample_account.id,
            category_id=sample_category.id,
            name="Plano Saude",
            amount=Decimal("400.00"),
            due_date=date.today(),
            bill_type=BillType.EXPENSE,
            recurrence=BillRecurrence.MONTHLY,
        )
        next_bill = ScheduledBillService.create_next_recurrence(
            db=db, bill_id=bill.id
        )
        assert next_bill is not None
        assert next_bill.due_date > bill.due_date
        assert next_bill.name == bill.name
