"""Cobertura da consolidação do Dashboard principal (Patrimônio + Recorrências)."""

from datetime import date, timedelta
from decimal import Decimal

from database.enums import AssetType, BillRecurrence, BillType
from database.models.account import Account
from database.models.scheduled_bill import ScheduledBill
from services.bill_recurrence_service import next_business_day
from services.dashboard_service import DashboardService
from services.investment_service import InvestmentService
from services.scheduled_bill_service import ScheduledBillService


def _create_account(db, user_id, balance):
    account = Account(
        user_id=user_id,
        name="Corretora",
        balance=balance,
        initial_balance=balance,
        is_active=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def test_wealth_summary_sums_cash_and_investments(db, sample_user):
    account = _create_account(db, sample_user.id, Decimal("3000.00"))
    asset = InvestmentService(db).register_asset(
        user_id=sample_user.id,
        ticker="IVVB11",
        name="ETF S&P 500",
        asset_type=AssetType.ETF,
    )

    InvestmentService(db).buy(
        asset_id=asset.id,
        user_id=sample_user.id,
        quantity="2",
        price_per_unit="1000",
        account_id=account.id,
        operation_date=date.today(),
        fees="0",
    )

    summary = DashboardService(db).get_wealth_summary(sample_user.id)

    assert summary["cash_balance"] == Decimal("1000.00")
    assert summary["investments_total"] == Decimal("2000.00")
    assert summary["net_worth"] == Decimal("3000.00")


def test_dashboard_lists_upcoming_recurrent_bills(db, sample_user, sample_account, sample_category):
    due = date.today() + timedelta(days=5)
    ScheduledBillService(db).create_bill(
        user_id=sample_user.id,
        name="Streaming",
        amount="49.90",
        bill_type=BillType.PAYABLE,
        due_date=due,
        account_id=sample_account.id,
        category_id=sample_category.id,
        recurrence=BillRecurrence.MONTHLY,
    )

    bills = DashboardService(db).get_upcoming_recurring_bills(sample_user.id, days_ahead=30)

    projected_due = next_business_day(due)
    assert len(bills) == 1
    assert bills[0]["name"] == "Streaming"
    assert bills[0]["due_date"] == projected_due.isoformat()
    assert bills[0]["bill_type"] == BillType.PAYABLE.value

    persisted = (
        db.query(ScheduledBill)
        .filter(ScheduledBill.user_id == sample_user.id, ScheduledBill.name == "Streaming")
        .one()
    )
    assert persisted.due_date == due
