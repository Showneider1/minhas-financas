"""ScheduledBillService — reescrito para a API REAL (instanciada, Decimal).

Missão 2 Fase 12: os testes antigos usavam API estática inexistente e enums
inexistentes (`BillType.EXPENSE/INCOME`; o real é PAYABLE/RECEIVABLE). Aqui cada
caso preserva a INTENÇÃO original contra o sistema real. Sem xfail/skip.

P0 novo comportamento coberto: pagar conta GERA o Transaction (rastreável).
"""
from datetime import date, timedelta
from decimal import Decimal

from database.models import ScheduledBill, BillStatus, BillType, BillRecurrence
from services.scheduled_bill_service import ScheduledBillService


def _svc(db) -> ScheduledBillService:
    return ScheduledBillService(db)


class TestScheduledBillService:

    def test_create_scheduled_bill(self, db, sample_user, sample_account, sample_category):
        bill = _svc(db).create_bill(
            user_id=sample_user.id,
            account_id=sample_account.id,
            category_id=sample_category.id,
            name="Aluguel",
            amount=Decimal("1500.00"),
            due_date=date.today() + timedelta(days=5),
            bill_type=BillType.PAYABLE,
            recurrence=BillRecurrence.MONTHLY,
        )
        assert bill.id is not None
        assert bill.name == "Aluguel"
        assert bill.amount == Decimal("1500.00")
        assert bill.status == BillStatus.PENDING

    def test_mark_bill_as_paid_generates_transaction(
        self, db, sample_user, sample_account, sample_category
    ):
        svc = _svc(db)
        bill = svc.create_bill(
            user_id=sample_user.id,
            account_id=sample_account.id,
            category_id=sample_category.id,
            name="Internet",
            amount=Decimal("120.00"),
            due_date=date.today() + timedelta(days=3),
            bill_type=BillType.PAYABLE,
        )
        paid = svc.mark_as_paid(bill.id, sample_user.id, paid_date=date.today())
        assert paid.status == BillStatus.PAID
        assert paid.paid_date == date.today()
        assert paid.paid_amount == Decimal("120.00")
        # P0: lançamento gerado e vinculado (rastreabilidade).
        from database.models.transaction import Transaction

        tx = (
            db.query(Transaction)
            .filter(Transaction.scheduled_bill_id == bill.id)
            .first()
        )
        assert tx is not None
        assert tx.base_amount == Decimal("120.00")
        assert tx.status.value == "PAID"
        # Idempotência: segundo pagamento não duplica.
        svc.mark_as_paid(bill.id, sample_user.id, paid_date=date.today())
        assert (
            db.query(Transaction)
            .filter(Transaction.scheduled_bill_id == bill.id)
            .count()
            == 1
        )

    def test_get_pending_bills_by_user(self, db, sample_user, sample_account, sample_category):
        svc = _svc(db)
        svc.create_bill(
            user_id=sample_user.id,
            account_id=sample_account.id,
            category_id=sample_category.id,
            name="Agua",
            amount=Decimal("80.00"),
            due_date=date.today() + timedelta(days=2),
            bill_type=BillType.PAYABLE,
        )
        pending = svc.list_bills(user_id=sample_user.id, status=BillStatus.PENDING)
        assert len(pending) >= 1

    def test_get_overdue_bills(self, db, sample_user, sample_account, sample_category):
        svc = _svc(db)
        svc.create_bill(
            user_id=sample_user.id,
            account_id=sample_account.id,
            category_id=sample_category.id,
            name="Conta Vencida",
            amount=Decimal("200.00"),
            due_date=date.today() - timedelta(days=5),
            bill_type=BillType.PAYABLE,
        )
        assert svc.update_overdue_bills(user_id=sample_user.id) >= 1
        overdue = svc.list_bills(user_id=sample_user.id, status=BillStatus.OVERDUE)
        assert len(overdue) >= 1

    def test_get_bills_due_soon(self, db, sample_user, sample_account, sample_category):
        svc = _svc(db)
        svc.create_bill(
            user_id=sample_user.id,
            account_id=sample_account.id,
            category_id=sample_category.id,
            name="Energia",
            amount=Decimal("300.00"),
            due_date=date.today() + timedelta(days=4),
            bill_type=BillType.PAYABLE,
        )
        upcoming = svc.get_upcoming_bills(user_id=sample_user.id, days_ahead=7)
        assert len(upcoming["due_this_week"]) >= 1

    def test_delete_bill_is_soft_delete(self, db, sample_user, sample_account, sample_category):
        svc = _svc(db)
        bill = svc.create_bill(
            user_id=sample_user.id,
            account_id=sample_account.id,
            category_id=sample_category.id,
            name="Assinatura Temp",
            amount=Decimal("50.00"),
            due_date=date.today() + timedelta(days=10),
            bill_type=BillType.PAYABLE,
        )
        bill_id = bill.id
        assert svc.delete_bill(bill_id, sample_user.id) is True
        row = db.query(ScheduledBill).filter(ScheduledBill.id == bill_id).first()
        assert row is not None and row.is_deleted is True
        assert svc.list_bills(user_id=sample_user.id) == []

    def test_get_bills_summary(self, db, sample_user, sample_account, sample_category):
        svc = _svc(db)
        svc.create_bill(
            user_id=sample_user.id,
            account_id=sample_account.id,
            category_id=sample_category.id,
            name="Salario",
            amount=Decimal("5000.00"),
            due_date=date.today() + timedelta(days=1),
            bill_type=BillType.RECEIVABLE,
            recurrence=BillRecurrence.MONTHLY,
        )
        summary = svc.get_upcoming_bills(user_id=sample_user.id)
        assert summary["total_receivable"] == Decimal("5000.00")
        assert summary["net_cash_flow"] == Decimal("5000.00")

    def test_pay_monthly_bill_generates_next_recurrence(
        self, db, sample_user, sample_account, sample_category
    ):
        svc = _svc(db)
        bill = svc.create_bill(
            user_id=sample_user.id,
            account_id=sample_account.id,
            category_id=sample_category.id,
            name="Plano Saude",
            amount=Decimal("400.00"),
            due_date=date.today(),
            bill_type=BillType.PAYABLE,
            recurrence=BillRecurrence.MONTHLY,
        )
        svc.mark_as_paid(bill.id, sample_user.id, paid_date=date.today())
        children = (
            db.query(ScheduledBill)
            .filter(ScheduledBill.parent_bill_id == bill.id)
            .all()
        )
        assert len(children) == 1
        assert children[0].due_date > bill.due_date
        assert children[0].name == bill.name
