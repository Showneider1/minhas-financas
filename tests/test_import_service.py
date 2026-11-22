"""Importação Bancária — CSV/OFX, deduplicação e isolamento por usuário."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from database.enums import TransactionType
from database.models.account import Account
from database.models.category import Category
from database.models.transaction import Transaction
from database.models.user import User
from schemas.transaction_schema import TransactionCreate
from services.balance_service import BalanceService
from services.finance_service import FinanceService
from services.import_service import (
    DUPLICATE_FOUND,
    READY_TO_IMPORT,
    ImportService,
    _parse_valor,
    import_from_csv,
)


def _ofx_content() -> bytes:
    return (
        b"OFXHEADER:100\n"
        b"DATA:OFXSGML\n"
        b"VERSION:102\n"
        b"SECURITY:NONE\n"
        b"ENCODING:USASCII\n"
        b"CHARSET:1252\n"
        b"COMPRESSION:NONE\n"
        b"OLDFILEUID:NONE\n"
        b"NEWFILEUID:NONE\n"
        b"\n"
        b"<OFX>\n"
        b"<SIGNONMSGSRSV1>\n"
        b"<SONRS>\n"
        b"<STATUS>\n"
        b"<CODE>0\n"
        b"<SEVERITY>INFO\n"
        b"</STATUS>\n"
        b"</SONRS>\n"
        b"</SIGNONMSGSRSV1>\n"
        b"<BANKMSGSRSV1>\n"
        b"<STMTTRNRS>\n"
        b"<STMTRS>\n"
        b"<CURDEF>BRL\n"
        b"<BANKACCTFROM>\n"
        b"<BANKID>123\n"
        b"<ACCTID>999\n"
        b"<ACCTTYPE>CHECKING\n"
        b"</BANKACCTFROM>\n"
        b"<BANKTRANLIST>\n"
        b"<DTSTART>20260301\n"
        b"<DTEND>20260331\n"
        b"<STMTTRN>\n"
        b"<TRNTYPE>DEBIT\n"
        b"<DTPOSTED>20260310\n"
        b"<TRNAMT>-100.50\n"
        b"<FITID>FITID-1\n"
        b"<NAME>Mercado\n"
        b"<MEMO>Purchase\n"
        b"</STMTTRN>\n"
        b"<STMTTRN>\n"
        b"<TRNTYPE>CREDIT\n"
        b"<DTPOSTED>20260311\n"
        b"<TRNAMT>5000.00\n"
        b"<FITID>FITID-2\n"
        b"<NAME>Salario\n"
        b"<MEMO>Payroll\n"
        b"</STMTTRN>\n"
        b"</BANKTRANLIST>\n"
        b"</STMTRS>\n"
        b"</STMTTRNRS>\n"
        b"</BANKMSGSRSV1>\n"
        b"</OFX>\n"
    )


def _create_manual_salary(
    db,
    user: User,
    account: Account,
    *,
    purchase_date: date,
    due_date: date,
    paid_date: date,
    description: str = "Salario ACME",
    amount: Decimal = Decimal("5000.00"),
) -> Transaction:
    """Lançamento manual pago (sem import_hash), via serviço canônico."""
    category = Category(
        user_id=user.id,
        name="Salario manual",
        transaction_type=TransactionType.INCOME,
        is_system=False,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return FinanceService(db).create_transaction(
        user.id,
        TransactionCreate(
            description=description,
            base_amount=amount,
            transaction_type=TransactionType.INCOME,
            category_id=category.id,
            account_id=account.id,
            purchase_date=purchase_date,
            due_date=due_date,
            paid_date=paid_date,
        ),
    )


def test_parse_valor_decimal():
    assert _parse_valor("1.234,56") == Decimal("1234.56")
    assert _parse_valor("1234.56") == Decimal("1234.56")
    assert _parse_valor("R$ 99,90") == Decimal("99.90")
    assert _parse_valor("-10,50") == Decimal("-10.50")


def test_import_csv_end_to_end_and_idempotent(db, sample_user, sample_account):
    csv = (
        b"data;descricao;valor\n"
        b"10/03/2026;Salario ACME;5000,00\n"
        b"11/03/2026;Mercado Central;-350,75\n"
    )

    r1 = import_from_csv(csv, sample_account.id, sample_user.id, db)
    assert r1["imported"] == 2
    assert r1["errors"] == []

    txs = db.query(Transaction).filter(Transaction.user_id == sample_user.id).all()
    assert len(txs) == 2
    assert all(isinstance(t.base_amount, Decimal) for t in txs)
    assert all(t.import_hash for t in txs)
    assert all(t.external_id for t in txs)

    r2 = import_from_csv(csv, sample_account.id, sample_user.id, db)
    assert r2["imported"] == 0
    assert r2["skipped"] == 2
    assert db.query(Transaction).filter(Transaction.user_id == sample_user.id).count() == 2


def test_import_moves_balance_and_reimport_is_idempotent(db, sample_user, sample_account):
    """Extratos são liquidações: movem saldo na 1ª importação e nunca na 2ª."""
    csv = (
        b"data;descricao;valor\n"
        b"10/03/2026;Salario ACME;5000,00\n"
        b"11/03/2026;Mercado Central;-350,75\n"
    )

    initial_balance = sample_account.initial_balance
    expected_balance = initial_balance + Decimal("5000.00") - Decimal("350.75")

    first = import_from_csv(csv, sample_account.id, sample_user.id, db)
    assert first["imported"] == 2
    assert first["errors"] == []
    imported = db.query(Transaction).filter(Transaction.user_id == sample_user.id).all()
    assert all(t.categorization_source == "import" for t in imported)

    db.refresh(sample_account)
    assert sample_account.balance == expected_balance
    assert BalanceService(db).reconcile(sample_user.id)["ok"] is True

    balance_after_first_import = sample_account.balance

    second = import_from_csv(csv, sample_account.id, sample_user.id, db)
    assert second["imported"] == 0
    assert second["skipped"] == 2
    assert second["errors"] == []

    db.refresh(sample_account)
    assert sample_account.balance == balance_after_first_import
    assert BalanceService(db).reconcile(sample_user.id)["ok"] is True


def test_import_detects_manual_collision_without_changing_balance(db, sample_user, sample_account):
    """Extrato não duplica lançamento manual já pago (mesma descrição/data/valor)."""
    csv = b"data;descricao;valor\n10/03/2026;Salario ACME;5000,00\n"

    category = Category(
        user_id=sample_user.id,
        name="Salario manual",
        transaction_type=TransactionType.INCOME,
        is_system=False,
    )
    db.add(category)
    db.commit()
    db.refresh(category)

    FinanceService(db).create_transaction(
        sample_user.id,
        TransactionCreate(
            description="Salario ACME",
            base_amount=Decimal("5000.00"),
            transaction_type=TransactionType.INCOME,
            category_id=category.id,
            account_id=sample_account.id,
            purchase_date=date(2026, 3, 10),
            due_date=date(2026, 3, 10),
            paid_date=date(2026, 3, 10),
        ),
    )
    db.refresh(sample_account)
    balance_before = sample_account.balance

    result = import_from_csv(csv, sample_account.id, sample_user.id, db)
    assert result["manual_conflicts"] == 1
    assert result["skipped"] == 1
    assert result["imported"] == 0
    assert result["errors"] == []
    assert db.query(Transaction).filter(Transaction.user_id == sample_user.id).count() == 1
    db.refresh(sample_account)
    assert sample_account.balance == balance_before

    manual = db.query(Transaction).filter(Transaction.user_id == sample_user.id).one()
    assert manual.import_hash is None
    assert manual.categorization_source == "manual"


def test_import_detects_manual_collision_by_due_date(db, sample_user, sample_account):
    """Manual com paid_date diverso, mas due_date igual ao extrato, é detectado."""
    csv = b"data;descricao;valor\n10/03/2026;Salario ACME;5000,00\n"
    _create_manual_salary(
        db,
        sample_user,
        sample_account,
        purchase_date=date(2026, 3, 1),
        due_date=date(2026, 3, 10),
        paid_date=date(2026, 3, 5),
    )

    result = import_from_csv(csv, sample_account.id, sample_user.id, db)
    assert result["manual_conflicts"] == 1
    assert result["skipped"] == 1
    assert result["imported"] == 0
    assert result["errors"] == []
    assert db.query(Transaction).filter(Transaction.user_id == sample_user.id).count() == 1


def test_manual_collision_is_consumed_only_once(db, sample_user, sample_account):
    """Uma manual não pode suprimir duas linhas legítimas do extrato."""
    # Descrições com espaçamento distinto → hashes diferentes, mesma transação.
    csv = (
        b"data;descricao;valor\n10/03/2026;Salario ACME;5000,00\n10/03/2026;Salario  ACME;5000,00\n"
    )
    _create_manual_salary(
        db,
        sample_user,
        sample_account,
        purchase_date=date(2026, 3, 10),
        due_date=date(2026, 3, 10),
        paid_date=date(2026, 3, 10),
    )
    db.refresh(sample_account)
    balance_before = sample_account.balance

    result = import_from_csv(csv, sample_account.id, sample_user.id, db)
    assert result["manual_conflicts"] == 1
    assert result["skipped"] == 1  # conflito manual também conta como skipped
    assert result["imported"] == 1
    assert result["errors"] == []
    assert db.query(Transaction).filter(Transaction.user_id == sample_user.id).count() == 2
    assert db.query(Transaction).filter(Transaction.import_hash.isnot(None)).count() == 1

    db.refresh(sample_account)
    assert sample_account.balance == balance_before + Decimal("5000.00")


def test_import_integrity_error_with_null_keys_goes_to_errors(
    db, sample_user, sample_account, monkeypatch
):
    """Chaves nulas não viram IS NULL (que casaria qualquer linha)."""

    def _boom(*args, **kwargs):
        raise IntegrityError("INSERT INTO transactions", {}, Exception("forced"))

    monkeypatch.setattr(FinanceService, "create_transaction", _boom)
    service = ImportService(db)
    rows = service.parse_file(
        b"data;descricao;valor\n10/03/2026;Salario ACME;5000,00\n",
        filename="extrato.csv",
        account_id=sample_account.id,
        user_id=sample_user.id,
    )
    rows[0]["external_id"] = None
    rows[0]["import_hash"] = None

    result = service.process_import(
        rows,
        category_ids=[rows[0]["suggested_category_id"]],
        account_id=sample_account.id,
        user_id=sample_user.id,
    )
    assert result["imported"] == 0
    assert result["skipped"] == 0
    assert result["errors"] and result["errors"][0]["line"] == 1
    assert db.query(Transaction).count() == 0


def test_import_integrity_error_without_conflict_goes_to_errors(
    db, sample_user, sample_account, monkeypatch
):
    """IntegrityError sem linha conflitante é erro — nunca duplicata silenciosa."""

    def _boom(*args, **kwargs):
        raise IntegrityError("INSERT INTO transactions", {}, Exception("forced"))

    monkeypatch.setattr(FinanceService, "create_transaction", _boom)
    csv = b"data;descricao;valor\n10/03/2026;Salario ACME;5000,00\n"

    result = import_from_csv(csv, sample_account.id, sample_user.id, db)
    assert result["imported"] == 0
    assert result["skipped"] == 0
    assert result["manual_conflicts"] == 0
    assert result["errors"] and result["errors"][0]["line"] == 1

    # rollback defensivo deixou a sessão utilizável
    assert db.query(Transaction).filter(Transaction.user_id == sample_user.id).count() == 0


def test_import_empty_csv_is_rejected(db, sample_user, sample_account):
    service = ImportService(db)
    with pytest.raises(ValueError):
        service.parse_file(
            b"",
            filename="extrato.csv",
            account_id=sample_account.id,
            user_id=sample_user.id,
        )


def test_import_unsupported_format_is_rejected(db, sample_user, sample_account):
    service = ImportService(db)
    with pytest.raises(ValueError):
        service.parse_file(
            b"dados",
            filename="extrato.txt",
            account_id=sample_account.id,
            user_id=sample_user.id,
        )


def test_import_process_with_no_rows_returns_empty_result(db, sample_user, sample_account):
    service = ImportService(db)
    result = service.process_import(
        [],
        category_ids=[],
        account_id=sample_account.id,
        user_id=sample_user.id,
    )
    assert result == {"imported": 0, "skipped": 0, "errors": [], "manual_conflicts": 0}


def test_parse_ofx_and_detect_duplicates(db, sample_user, sample_account):
    service = ImportService(db)

    rows = service.parse_file(
        _ofx_content(),
        filename="extrato.ofx",
        account_id=sample_account.id,
        user_id=sample_user.id,
    )

    assert len(rows) == 2
    assert all(row["status"] == READY_TO_IMPORT for row in rows)
    assert rows[0]["amount"] == "100.50"
    assert rows[0]["transaction_type"] == "EXPENSE"
    assert rows[1]["amount"] == "5000.00"
    assert rows[1]["transaction_type"] == "INCOME"
    assert rows[0]["external_id"].startswith("ofx:")
    assert rows[1]["external_id"].startswith("ofx:")

    category_ids = [row["suggested_category_id"] for row in rows]
    result = service.process_import(
        rows,
        category_ids=category_ids,
        account_id=sample_account.id,
        user_id=sample_user.id,
    )

    assert result["imported"] == 2
    assert result["errors"] == []

    second_rows = service.parse_file(
        _ofx_content(),
        filename="extrato.ofx",
        account_id=sample_account.id,
        user_id=sample_user.id,
    )
    assert all(row["status"] == DUPLICATE_FOUND for row in second_rows)

    second_result = service.process_import(
        second_rows,
        category_ids=category_ids,
        account_id=sample_account.id,
        user_id=sample_user.id,
    )
    assert second_result["imported"] == 0
    assert second_result["skipped"] == 2


def test_import_isolates_users(db, sample_user, sample_account):
    service = ImportService(db)

    first_rows = service.parse_file(
        _ofx_content(),
        filename="extrato.ofx",
        account_id=sample_account.id,
        user_id=sample_user.id,
    )
    first_result = service.process_import(
        first_rows,
        category_ids=[row["suggested_category_id"] for row in first_rows],
        account_id=sample_account.id,
        user_id=sample_user.id,
    )
    assert first_result["imported"] == 2

    other_user = User(
        name="Outro Usuário",
        email="outro-import@email.com",
        password_hash="hash",
        is_active=True,
        is_deleted=False,
    )
    db.add(other_user)
    db.commit()
    db.refresh(other_user)

    other_account = Account(
        user_id=other_user.id,
        name="Conta Outro Usuário",
        balance=Decimal("0.00"),
        initial_balance=Decimal("0.00"),
        is_active=True,
    )
    db.add(other_account)
    db.commit()
    db.refresh(other_account)

    other_rows = service.parse_file(
        _ofx_content(),
        filename="extrato.ofx",
        account_id=other_account.id,
        user_id=other_user.id,
    )
    assert all(row["status"] == READY_TO_IMPORT for row in other_rows)

    other_result = service.process_import(
        other_rows,
        category_ids=[row["suggested_category_id"] for row in other_rows],
        account_id=other_account.id,
        user_id=other_user.id,
    )
    assert other_result["imported"] == 2

    assert db.query(Transaction).filter(Transaction.user_id == sample_user.id).count() == 2
    assert db.query(Transaction).filter(Transaction.user_id == other_user.id).count() == 2
