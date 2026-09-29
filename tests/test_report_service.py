"""Testes do ReportService — exportação mensal e isolamento por usuário."""

from datetime import date
from decimal import Decimal

from database.enums import TransactionStatus, TransactionType
from database.models.category import Category
from database.models.transaction import Transaction
from database.models.user import User
from services.report_service import ReportService


def _create_transaction(
    db,
    user_id,
    account_id,
    category_id,
    *,
    amount,
    due_date,
    description="Transação",
    status=TransactionStatus.PAID,
):
    transaction = Transaction(
        user_id=user_id,
        account_id=account_id,
        category_id=category_id,
        description=description,
        base_amount=Decimal(amount),
        transaction_type=TransactionType.EXPENSE,
        purchase_date=due_date,
        due_date=due_date,
        paid_date=due_date if status == TransactionStatus.PAID else None,
        status=status,
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def test_monthly_extract_contains_expected_columns_and_rows(
    db, sample_user, sample_account, sample_category
):
    _create_transaction(
        db,
        sample_user.id,
        sample_account.id,
        sample_category.id,
        amount="100.50",
        due_date=date(2026, 9, 10),
        description="Mercado",
    )
    _create_transaction(
        db,
        sample_user.id,
        sample_account.id,
        sample_category.id,
        amount="49.90",
        due_date=date(2026, 9, 20),
        description="Farmácia",
    )

    report = ReportService(db).generate_monthly_extract(
        sample_user.id,
        month=9,
        year=2026,
    )

    assert list(report.columns) == [
        "Data",
        "Descrição",
        "Categoria",
        "Tipo",
        "Conta Origem",
        "Valor",
        "Status",
    ]
    assert len(report) == 2
    assert report.iloc[0]["Descrição"] == "Mercado"
    assert report.iloc[0]["Valor"] == "100,50"
    assert report.iloc[1]["Valor"] == "49,90"
    assert report.iloc[0]["Tipo"] == "Despesa"
    assert report.iloc[0]["Status"] == "Pago"


def test_monthly_extract_isolates_users(db, sample_user, sample_account, sample_category):
    other_user = User(
        name="Outro Usuário",
        email="outro-report@email.com",
        password_hash="hash",
        is_active=True,
        is_deleted=False,
    )
    db.add(other_user)
    db.commit()
    db.refresh(other_user)

    other_category = Category(
        user_id=other_user.id,
        name="Outros Gastos",
        transaction_type=TransactionType.EXPENSE,
        is_system=False,
    )
    db.add(other_category)
    db.commit()
    db.refresh(other_category)

    _create_transaction(
        db,
        sample_user.id,
        sample_account.id,
        sample_category.id,
        amount="100.00",
        due_date=date(2026, 9, 1),
        description="Minha despesa",
    )
    _create_transaction(
        db,
        other_user.id,
        sample_account.id,
        other_category.id,
        amount="999.00",
        due_date=date(2026, 9, 2),
        description="Despesa de outro usuário",
    )

    report = ReportService(db).generate_monthly_extract(
        sample_user.id,
        month=9,
        year=2026,
    )

    assert len(report) == 1
    assert report.iloc[0]["Descrição"] == "Minha despesa"
    assert "Despesa de outro usuário" not in set(report["Descrição"])


def test_monthly_extract_respects_month_and_year(db, sample_user, sample_account, sample_category):
    _create_transaction(
        db,
        sample_user.id,
        sample_account.id,
        sample_category.id,
        amount="100.00",
        due_date=date(2026, 8, 31),
        description="Agosto",
    )
    _create_transaction(
        db,
        sample_user.id,
        sample_account.id,
        sample_category.id,
        amount="200.00",
        due_date=date(2026, 9, 1),
        description="Setembro",
    )

    report = ReportService(db).generate_monthly_extract(
        sample_user.id,
        month=9,
        year=2026,
    )

    assert len(report) == 1
    assert report.iloc[0]["Descrição"] == "Setembro"


def test_monthly_extract_preserves_decimal_precision(
    db, sample_user, sample_account, sample_category
):
    _create_transaction(
        db,
        sample_user.id,
        sample_account.id,
        sample_category.id,
        amount="123456.78",
        due_date=date(2026, 9, 15),
        description="Compra cara",
    )

    report = ReportService(db).generate_monthly_extract(
        sample_user.id,
        month=9,
        year=2026,
    )

    assert report.iloc[0]["Valor"] == "123456,78"


def test_budget_closing_generates_readable_report(db, sample_user, sample_account, sample_category):
    from services.budget_service import BudgetService

    BudgetService(db).set_budget(
        user_id=sample_user.id,
        category_id=sample_category.id,
        month=9,
        year=2026,
        amount_limit=Decimal("500.00"),
    )
    _create_transaction(
        db,
        sample_user.id,
        sample_account.id,
        sample_category.id,
        amount="250.00",
        due_date=date(2026, 9, 12),
        description="Gasto do orçamento",
    )

    report = ReportService(db).generate_budget_closing(
        sample_user.id,
        month=9,
        year=2026,
    )

    assert list(report.columns) == ["Categoria", "Limite", "Gasto", "% Usado", "Status"]
    assert report.iloc[0]["Limite"] == "500,00"
    assert report.iloc[0]["Gasto"] == "250,00"
    assert report.iloc[0]["% Usado"] == "50,0"
    assert report.iloc[0]["Status"] == "OK"
