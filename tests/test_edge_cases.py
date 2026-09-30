"""Edge cases — usuário vazio, integração cruzada e resiliência offline."""

from datetime import date
from decimal import Decimal

from database.enums import AssetType, TransactionType
from database.models.account import Account
from database.models.transaction import Transaction
from services.analytics_service import AnalyticsService
from services.budget_service import BudgetService
from services.credit_card_service import CreditCardService
from services.dashboard_service import DashboardService
from services.investment_service import InvestmentService
from services.market_data_service import MarketDataService
from services.report_service import ReportService


def test_day_one_dashboard_executive_summary_is_zero_safe(db, sample_user):
    summary = DashboardService(db).get_executive_summary(
        sample_user.id,
        month=date.today().month,
        year=date.today().year,
    )

    assert summary["cash_balance"] == Decimal("0.00")
    assert summary["total_invested"] == Decimal("0.00")
    assert summary["investments_market_value"] == Decimal("0.00")
    assert summary["open_invoices"] == Decimal("0.00")
    assert summary["net_worth"] == Decimal("0.00")
    assert summary["budget_alerts"] == []
    assert summary["cash_flow"]["income_paid"] == Decimal("0.00")
    assert summary["cash_flow"]["expense_paid"] == Decimal("0.00")


def test_day_one_analytics_is_zero_safe(db, sample_user):
    analytics = AnalyticsService(db)
    categories = analytics.get_expenses_by_category(
        sample_user.id,
        month=date.today().month,
        year=date.today().year,
    )
    cash_flow = analytics.get_cash_flow_history(sample_user.id, limit_months=6)

    assert categories == []
    assert len(cash_flow) == 6
    assert all(item["income"] == Decimal("0.00") for item in cash_flow)
    assert all(item["expenses"] == Decimal("0.00") for item in cash_flow)
    assert all(item["net"] == Decimal("0.00") for item in cash_flow)


def test_day_one_investments_and_budgets_are_zero_safe(db, sample_user):
    investments = InvestmentService(db).get_position_summary(sample_user.id)
    budgets = BudgetService(db).get_budget_progress(
        sample_user.id,
        month=date.today().month,
        year=date.today().year,
    )

    assert investments["total_current_value"] == Decimal("0.00")
    assert investments["total_cost"] == Decimal("0.00")
    assert investments["positions"] == []
    assert budgets == []


def test_day_one_reports_return_empty_but_valid_dataframes(db, sample_user):
    report_service = ReportService(db)
    monthly = report_service.generate_monthly_extract(
        sample_user.id,
        month=date.today().month,
        year=date.today().year,
    )
    budget_closing = report_service.generate_budget_closing(
        sample_user.id,
        month=date.today().month,
        year=date.today().year,
    )

    assert monthly.empty is True
    assert list(monthly.columns) == [
        "Data",
        "Descrição",
        "Categoria",
        "Tipo",
        "Conta Origem",
        "Valor",
        "Status",
    ]
    assert budget_closing.empty is True
    assert list(budget_closing.columns) == [
        "Categoria",
        "Limite",
        "Gasto",
        "% Usado",
        "Status",
    ]


def test_market_data_falls_back_for_invalid_ticker(db):
    class _FailingProvider:
        def Ticker(self, symbol):
            raise RuntimeError("Sem internet")

    service = MarketDataService(db, provider=_FailingProvider())

    price = service.get_current_price(
        "TICKER_FALSO3",
        fallback_price=Decimal("12.34"),
    )

    assert price == Decimal("12.34")


def test_monthly_report_supports_investments_and_invoice_payments(db, sample_user, sample_category):
    account = Account(
        user_id=sample_user.id,
        name="Corretora",
        balance=Decimal("20000.00"),
        initial_balance=Decimal("20000.00"),
        is_active=True,
    )
    db.add(account)
    db.commit()
    db.refresh(account)

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
        quantity="100",
        price_per_unit="100.00",
        account_id=account.id,
        operation_date=date.today(),
        fees="0",
    )
    investment_service.record_dividend(
        asset_id=asset.id,
        user_id=sample_user.id,
        amount="250.00",
        account_id=account.id,
        operation_date=date.today(),
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
        amount=Decimal("500.00"),
        purchase_date=date.today(),
        description="Compra no cartão",
        category_id=sample_category.id,
        installments=1,
    )
    card_transactions = card_service.register_purchase(
        user_id=sample_user.id,
        credit_card_id=card.id,
        amount=Decimal("100.00"),
        purchase_date=date.today().replace(day=1),
        description="Compra no cartão do ciclo atual",
        category_id=sample_category.id,
        installments=1,
    )
    invoice_month = card_transactions[0].due_date.month
    invoice_year = card_transactions[0].due_date.year
    card_service.pay_invoice(
        user_id=sample_user.id,
        credit_card_id=card.id,
        month=invoice_month,
        year=invoice_year,
        source_account_id=account.id,
        payment_date=date.today(),
    )

    report = ReportService(db).generate_monthly_extract(
        sample_user.id,
        month=date.today().month,
        year=date.today().year,
    )

    assert not report.empty
    types = set(report["Tipo"])
    assert {"Receita", "Despesa", "Transferência"} <= types
    assert "Compra PETR4 100.00000000 × 100.00000000" in set(report["Descrição"])
    assert "Dividendo PETR4 0 × 0" in set(report["Descrição"])
    assert "Compra no cartão do ciclo atual" in set(report["Descrição"])
    assert any("Pagamento da fatura Nubank" in description for description in report["Descrição"])


def test_budget_ignores_invoice_payment_transfer(db, sample_user, sample_account, sample_category):
    BudgetService(db).set_budget(
        user_id=sample_user.id,
        category_id=sample_category.id,
        month=date.today().month,
        year=date.today().year,
        amount_limit=Decimal("1000.00"),
    )

    transfer = Transaction(
        user_id=sample_user.id,
        account_id=sample_account.id,
        category_id=sample_category.id,
        description="Pagamento de fatura",
        base_amount=Decimal("500.00"),
        transaction_type=TransactionType.TRANSFER,
        purchase_date=date.today(),
        due_date=date.today(),
        paid_date=date.today(),
        status="PAID",
    )
    db.add(transfer)
    db.commit()

    progress = BudgetService(db).get_budget_progress(
        sample_user.id,
        month=date.today().month,
        year=date.today().year,
    )

    assert len(progress) == 1
    assert progress[0].spent == Decimal("0.00")
    assert progress[0].percentage == 0.0
    assert progress[0].status == "OK"
