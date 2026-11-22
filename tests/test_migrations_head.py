"""Regressão: a cadeia Alembic deve aplicar do zero até o head.

Cobria-se apenas `create_all()`, então a migration `a1b2c3d4e5f6` ficou
quebrada por muito tempo (CHECK (amount > 0) sobrevivia ao rename no SQLite).
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_alembic_upgrade_head_applies_cleanly_on_fresh_database(tmp_path):
    db_path = tmp_path / "fresh.db"
    url = f"sqlite:///{db_path.as_posix()}"
    env = {**os.environ, "DATABASE_URL": url, "WSLENV": "DATABASE_URL"}

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr

    connection = sqlite3.connect(db_path)
    try:
        version = connection.execute("select version_num from alembic_version").fetchone()
        assert version == ("f1a5b599f589",)

        budgets_columns = {row[1] for row in connection.execute("pragma table_info(budgets)")}
        assert "amount_limit" in budgets_columns
        assert "amount" not in budgets_columns

        budgets_sql = connection.execute(
            "select sql from sqlite_master where name = 'budgets'"
        ).fetchone()[0]
        assert 'check ("amount_limit" > 0)' in budgets_sql.casefold()

        tables = {
            row[0]
            for row in connection.execute("select name from sqlite_master where type = 'table'")
        }
        assert {"vaults", "credit_cards", "asset_prices", "refresh_tokens"} <= tables
    finally:
        connection.close()
