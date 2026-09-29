"""Testes do Dashboard Executivo (Visão 360)."""

from datetime import date
from decimal import Decimal

from database.enums import AssetType, TransactionStatus, TransactionType
from database.models.account import Account
from database.models.transaction import Transaction
from services.budget_service import BudgetService
from services.credit_card_service import CreditCardService
from services.dashboard_service import DashboardService
from services.investment_service import InvestmentService


def _create_account(db, user_id, balance):
    account = Account(
        user_id=user_id,
        name="Conta Executiva",
        balance=Decimal(balance),
        initial_balance=Decimal(balance),
        is_active=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def test_executive_summary_net_worth_subtracts_open_invoices(db, sample_user, sample_category):
    account = _create_account(db, sample_user.id, "15000.00")
    investment_service = InvestmentService(db)
    asset = investment_service.register_asset(
        user_id=sample_user.id,
        ticker="PETR4",
        name="Petrobras PN",
        asset_type=AssetType.STOCK,
    )
    investment_service.buy(
        asset_id=asset.id,
        user_id=sample_user.id,
        quantity="1000",
        price_per_unit="10.00",
        account_id=account.id,
        operation_date=date.today(),
        fees="0",
    )

    card_service = CreditCardService(db)
    card = card_service.create_credit_card(
        user_id=sample_user.id,
        name="Nubank",
        credit_limit=Decimal("5000.00"),
        closing_day=3,
        due_day=10,
    )
    card_service.register_purchase(
        user_id=sample_user.id,
        credit_card_id=card.id,
        amount=Decimal("2000.00"),
        purchase_date=date.today(),
        description="Compra parcelada",
        category_id=sample_category.id,
        installments=1,
    )

    summary = DashboardService(db).get_executive_summary(
        sample_user.id,
        month=date.today().month,
        year=date.today().year,
    )

    assert summary["cash_balance"] == Decimal("5000.00")
    assert summary["total_invested"] == Decimal("10000.00")
    assert summary["open_invoices"] == Decimal("2000.00")
    assert summary["net_worth"] == Decimal("13000.00")


def test_executive_summary_includes_budget_alerts_above_80(
    db, sample_user, sample_account, sample_category
):
    budget_service = BudgetService(db)
    budget_service.set_budget(
        user_id=sample_user.id,
        category_id=sample_category.id,
        month=date.today().month,
        year=date.today().year,
        amount_limit=Decimal("100.00"),
    )

    expense = Transaction(
        user_id=sample_user.id,
        account_id=sample_account.id,
        category_id=sample_category.id,
        description="Despesa orçada",
        base_amount=Decimal("90.00"),
        transaction_type=TransactionType.EXPENSE,
        purchase_date=date.today(),
        due_date=date.today(),
        paid_date=None,
        status=TransactionStatus.PENDING,
    )
    db.add(expense)
    db.commit()

    summary = DashboardService(db).get_executive_summary(
        sample_user.id,
        month=date.today().month,
        year=date.today().year,
    )

    assert len(summary["budget_alerts"]) == 1
    alert = summary["budget_alerts"][0]
    assert alert["category_name"] == sample_category.name
    assert alert["amount_limit"] == Decimal("100.00")
    assert alert["spent"] == Decimal("90.00")
    assert alert["percentage"] == 90.0
