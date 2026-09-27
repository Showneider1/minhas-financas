"""ETL SQLite -> PostgreSQL (staging, sem cutover).

Uso:
    MIGRATION_TARGET_URL="postgresql://...:6543/postgres?sslmode=require" \
      venv/Scripts/python.exe scripts/migrate_sqlite_to_postgres.py
    # ou, para validação local da lógica (sem Postgres):
    MIGRATION_TARGET_URL="sqlite:///./data/.etl_validate.db" \
      venv/Scripts/python.exe scripts/migrate_sqlite_to_postgres.py

Regras:
- Fonte SOMENTE leitura: sqlite:///./data/finance.db (nunca alterado).
- Ordem de integridade referencial; IDs exatos preservados.
- Valores monetários quantizados (Q2 dinheiro, Q4 qty/preço) via Decimal(str()).
- Falha ALTA em qualquer IntegrityError (rollback por tabela + raise).
- Postgres: ajusta sequences (setval) após cada tabela com PK inteira.
- `login_attempts` (operacional/rate-limit) NÃO é migrado, por design.
- Idempotente por chave natural: re-execução falha em UNIQUE (não duplica
  silenciosamente) — para recarga limpa, recrie o schema destino.

Target URL nunca é logada (pode conter senha).
"""
import os
import sys
from decimal import Decimal
from typing import Dict, List

SOURCE_URL = "sqlite:///./data/finance.db"

# Ordem de integridade referencial (pais antes dos filhos).
TABLE_ORDER: List[str] = [
    "users",
    "accounts",
    "categories",
    "budgets",
    "goals",
    "scheduled_bills",
    "assets",
    "transactions",
    "investment_operations",
    "password_reset_tokens",
]

# Colunas monetárias: tabela -> {coluna: casas}. Quantização determinística.
MONEY_Q2: Dict[str, List[str]] = {
    "accounts": ["balance", "initial_balance", "credit_limit"],
    "transactions": ["base_amount"],
    "budgets": ["amount"],
    "goals": ["target_amount", "current_amount", "monthly_contribution"],
    "scheduled_bills": ["amount", "paid_amount"],
}
MONEY_Q4: Dict[str, List[str]] = {
    "investment_operations": ["quantity", "price_per_unit", "fees", "total_amount"],
}


def _quantize(table: str, row: dict) -> dict:
    out = dict(row)
    for col in MONEY_Q2.get(table, []):
        if out.get(col) is not None:
            out[col] = Decimal(str(out[col])).quantize(Decimal("0.01"))
    for col in MONEY_Q4.get(table, []):
        if out.get(col) is not None:
            out[col] = Decimal(str(out[col])).quantize(Decimal("0.0001"))
    return out


def _target_url() -> str:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    url = os.getenv("MIGRATION_TARGET_URL", "").strip()
    if not url or "PREENCHER_OFFLINE" in url or "[USER]" in url:
        print(
            "MIGRATION_TARGET_URL ausente (ou ainda com placeholder offline). "
            "Defina com a URL do banco destino (Supabase pooler em staging; "
            "sqlite local só p/ validação)."
        )
        sys.exit(2)
    return url


def main() -> int:
    from sqlalchemy import create_engine, MetaData, Table, select, func

    target_url = _target_url()
    is_pg = target_url.startswith(("postgresql://", "postgres://"))

    src = create_engine(SOURCE_URL)
    dst = create_engine(target_url)

    src_meta = MetaData()
    src_meta.reflect(bind=src)
    dst_meta = MetaData()
    dst_meta.reflect(bind=dst)
    missing = [t for t in TABLE_ORDER if t not in dst_meta.tables]
    if missing:
        print(f"ETL: schema destino incompleto (faltam: {missing}).")
        print("ETL: aplique o schema antes: alembic upgrade head no banco destino.")
        return 1

    print(f"ETL: origem=sqlite local | destino={'postgres' if is_pg else 'sqlite'} | tabelas={len(TABLE_ORDER)}")
    totals = {}
    with src.connect() as sconn, dst.connect() as dconn:
        for name in TABLE_ORDER:
            stable: Table = src_meta.tables[name]
            dtable: Table = dst_meta.tables[name]
            cols = [c.name for c in stable.columns]
            rows = sconn.execute(select(stable)).mappings().all()
            read_n = len(rows)
            inserted = 0
            trans = dconn.begin_nested()
            try:
                for r in rows:
                    payload = _quantize(name, {c: r[c] for c in cols})
                    dconn.execute(dtable.insert().values(**payload))
                    inserted += 1
                trans.commit()
            except Exception as exc:
                trans.rollback()
                print(f"ETL: FALHA em '{name}' após {inserted}/{read_n} linhas: {type(exc).__name__}: {exc}")
                print("ETL: rollback da tabela; nada parcial foi confirmado. Abortando.")
                return 1
            # Confere contagem no destino.
            have = dconn.execute(select(func.count()).select_from(dtable)).scalar()
            status = "OK" if have == read_n else "DIVERGENTE"
            print(f"ETL: {name:22s} lidas={read_n:4d} inseridas={inserted:4d} destino={have:4d} [{status}]")
            if have != read_n:
                return 1
            totals[name] = (read_n, inserted)
            if is_pg and read_n:
                # Sequences dos IDs preservados: próximo INSERT usa max+1.
                seq = dconn.execute(
                    select(func.pg_catalog.pg_get_serial_sequence(name, "id"))
                ).scalar()
                mx = dconn.execute(select(func.max(dtable.c.id))).scalar()
                if seq and mx:
                    dconn.execute(select(func.pg_catalog.setval(seq, mx)))
                dconn.commit()
        dconn.commit()
    print(f"ETL: concluído — {sum(r for r, _ in totals.values())} linhas em {len(totals)} tabelas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
