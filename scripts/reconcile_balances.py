"""Reconciliação matemática origem × destino (prova de conceito).

Uso:
    MIGRATION_TARGET_URL="<url destino>" \
      venv/Scripts/python.exe scripts/reconcile_balances.py

Compara, por usuário e conta, o saldo calculado pelo MESMO BalanceService
nos dois bancos, além de contagens e somas por (tipo, status).
SUCESSO = todas as diferenças exatamente ZERO (exit 0).
Qualquer divergência imprime a linha e exit 1.

URLs nunca são logadas.
"""
import os
import sys
from decimal import Decimal

SOURCE_URL = "sqlite:///./data/finance.db"

TABLES_COUNT = [
    "users", "accounts", "categories", "transactions", "budgets",
    "goals", "scheduled_bills", "assets", "investment_operations",
    "password_reset_tokens",
]


def _target_url() -> str:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    url = os.getenv("MIGRATION_TARGET_URL", "").strip()
    if not url:
        print("MIGRATION_TARGET_URL ausente — nada a reconciliar.")
        sys.exit(2)
    return url


def main() -> int:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from database.base import Base
    import database.models  # noqa: F401 — registra metadata p/ tipos
    from database.models.account import Account
    from services.balance_service import BalanceService

    target_url = _target_url()
    src_engine = create_engine(SOURCE_URL)
    dst_engine = create_engine(target_url)
    SrcSession = sessionmaker(bind=src_engine)
    DstSession = sessionmaker(bind=dst_engine)

    failures = 0
    with SrcSession() as sdb, DstSession() as ddb:
        # 1. Contagens por tabela.
        print("== contagens (origem × destino) ==")
        for name in TABLES_COUNT:
            table = Base.metadata.tables[name]
            sc = sdb.query(table).count()
            dc = ddb.query(table).count()
            mark = "OK" if sc == dc else "DIVERGENTE"
            print(f"{name:22s} origem={sc:4d} destino={dc:4d} [{mark}]")
            if sc != dc:
                failures += 1

        # 2. Saldos por conta (mesmo motor, dois bancos).
        print("== saldos por conta (BalanceService) ==")
        for acc in sdb.query(Account).order_by(Account.id).all():
            expected = BalanceService(sdb).get_account_balance(acc.id, acc.user_id)
            try:
                got = BalanceService(ddb).get_account_balance(acc.id, acc.user_id)
            except LookupError:
                got = None
            diff = None if got is None else (expected - got)
            ok = diff == 0
            print(
                f"conta {acc.id} ({acc.name}): origem={expected} destino={got} "
                f"diff={diff} [{'OK' if ok else 'DIVERGENTE'}]"
            )
            if not ok:
                failures += 1

        # 3. Somas por (tipo, status) — quantizadas no centavo (unidade contábil).
        print("== somas por tipo/status ==")
        from database.models.transaction import Transaction
        from sqlalchemy import func
        from utils.money import to_money2

        def _sums(db):
            return {
                (t.value, s.value): to_money2(v or 0, where="reconcile")
                for t, s, v in db.query(
                    Transaction.transaction_type, Transaction.status,
                    func.sum(Transaction.base_amount),
                ).group_by(Transaction.transaction_type, Transaction.status).all()
            }

        s_map, d_map = _sums(sdb), _sums(ddb)
        for key in sorted(set(s_map) | set(d_map)):
            mark = "OK" if s_map.get(key) == d_map.get(key) else "DIVERGENTE"
            print(f"{key}: origem={s_map.get(key)} destino={d_map.get(key)} [{mark}]")
        if s_map != d_map:
            print("DIVERGÊNCIA nas somas por tipo/status.")
            failures += 1
        else:
            print("somas por tipo/status: OK (idênticas)")

    if failures:
        print(f"RECONCILIAÇÃO: {failures} divergência(s) — NÃO migrar.")
        return 1
    print("RECONCILIAÇÃO: todas as diferenças ZERO. Staging íntegro.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
