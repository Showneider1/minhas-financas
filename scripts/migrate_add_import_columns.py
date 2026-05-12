"""
Migration manual: adiciona colunas de importacao bancaria na tabela transactions.

Colunas adicionadas:
    - import_hash (TEXT, UNIQUE): hash SHA256 para deduplicacao de lancamentos importados
    - categorization_source (TEXT, DEFAULT 'manual'): origem da categorizacao (manual/auto/import)

Execucao (uma unica vez, no ambiente local ou de producao):
    python scripts/migrate_add_import_columns.py

Seguro para rodar multiplas vezes: verifica se a coluna ja existe antes de alterar.
=======
- import_hash (TEXT, UNIQUE): hash SHA256 para deduplicacao
- categorization_source (TEXT, DEFAULT 'manual'): origem da categorizacao

Execucao:
    python scripts/migrate_add_import_columns.py
>>>>>>> f08a7a0 (fix(dashboard): corrige KPIs, saldo calculado dinamicamente e gráficos de categoria)
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

<<<<<<< HEAD
=======
from sqlalchemy import text
>>>>>>> f08a7a0 (fix(dashboard): corrige KPIs, saldo calculado dinamicamente e gráficos de categoria)
from database.connection import get_db_session
from config.logging_config import app_logger


def column_exists(db, table: str, column: str) -> bool:
<<<<<<< HEAD
    """Verifica se a coluna ja existe para evitar erro no segundo run."""
    result = db.execute(f"PRAGMA table_info({table})").fetchall()
=======
    result = db.execute(text(f"PRAGMA table_info({table})")).fetchall()
>>>>>>> f08a7a0 (fix(dashboard): corrige KPIs, saldo calculado dinamicamente e gráficos de categoria)
    return any(row[1] == column for row in result)


def run_migration():
    print("=" * 60)
    print("Migration: add import_hash + categorization_source")
    print("Tabela: transactions")
    print("=" * 60)

    try:
        with get_db_session() as db:
<<<<<<< HEAD

            # --------------------------------------------------
            # Coluna 1: import_hash
            # Hash SHA256 para identificar duplicatas na importacao
            # --------------------------------------------------
            if not column_exists(db, "transactions", "import_hash"):
                db.execute(
                    "ALTER TABLE transactions ADD COLUMN import_hash TEXT"
                )
                db.execute(
=======
            if not column_exists(db, "transactions", "import_hash"):
                db.execute(text("ALTER TABLE transactions ADD COLUMN import_hash TEXT"))
                db.execute(text(
>>>>>>> f08a7a0 (fix(dashboard): corrige KPIs, saldo calculado dinamicamente e gráficos de categoria)
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    "idx_transactions_import_hash "
                    "ON transactions(import_hash) "
                    "WHERE import_hash IS NOT NULL"
<<<<<<< HEAD
                )
=======
                ))
>>>>>>> f08a7a0 (fix(dashboard): corrige KPIs, saldo calculado dinamicamente e gráficos de categoria)
                db.commit()
                print("[OK] Coluna 'import_hash' adicionada com indice unico.")
            else:
                print("[--] Coluna 'import_hash' ja existe. Ignorado.")

<<<<<<< HEAD
            # --------------------------------------------------
            # Coluna 2: categorization_source
            # Origem da categorizacao: manual | auto | import
            # --------------------------------------------------
            if not column_exists(db, "transactions", "categorization_source"):
                db.execute(
                    "ALTER TABLE transactions "
                    "ADD COLUMN categorization_source TEXT DEFAULT 'manual'"
                )
=======
            if not column_exists(db, "transactions", "categorization_source"):
                db.execute(text(
                    "ALTER TABLE transactions "
                    "ADD COLUMN categorization_source TEXT DEFAULT 'manual'"
                ))
>>>>>>> f08a7a0 (fix(dashboard): corrige KPIs, saldo calculado dinamicamente e gráficos de categoria)
                db.commit()
                print("[OK] Coluna 'categorization_source' adicionada.")
            else:
                print("[--] Coluna 'categorization_source' ja existe. Ignorado.")

        print("=" * 60)
        print("Migration concluida com sucesso!")
        print("=" * 60)

    except Exception as exc:
        print(f"[ERRO] Falha durante a migration: {exc}")
        app_logger.error(f"[Migration] Erro: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
<<<<<<< HEAD
    run_migration()
=======
    run_migration()
>>>>>>> f08a7a0 (fix(dashboard): corrige KPIs, saldo calculado dinamicamente e gráficos de categoria)
