"""Importação CSV — Decimal, contrato canônico e idempotência (Missão 2 Fase 3).

Cobre: parse BR/ISO sem float, fallback de categoria, geração via
FinanceService (saldos movem), duplicata ignorada via import_hash.
"""
from decimal import Decimal

from services.import_service import _parse_valor, import_from_csv


def test_parse_valor_decimal():
    assert _parse_valor("1.234,56") == Decimal("1234.56")
    assert _parse_valor("1234.56") == Decimal("1234.56")
    assert _parse_valor("R$ 99,90") == Decimal("99.90")
    assert _parse_valor("-10,50") == Decimal("-10.50")


def test_import_csv_end_to_end_and_idempotent(db, sample_user, sample_account):
    csv = (
        "data;descricao;valor\n"
        "10/03/2026;Salario ACME;5000,00\n"
        "11/03/2026;Mercado Central;-350,75\n"
    ).encode("utf-8")

    r1 = import_from_csv(csv, sample_account.id, sample_user.id, db)
    assert r1["imported"] == 2
    assert r1["errors"] == []

    from database.models.transaction import Transaction

    txs = db.query(Transaction).filter(Transaction.user_id == sample_user.id).all()
    assert len(txs) == 2
    assert all(isinstance(t.base_amount, Decimal) for t in txs)
    assert all(t.import_hash for t in txs)

    r2 = import_from_csv(csv, sample_account.id, sample_user.id, db)
    assert r2["imported"] == 0
    assert r2["skipped"] == 2
    assert db.query(Transaction).filter(Transaction.user_id == sample_user.id).count() == 2
