"""p2 budgets amount_limit

Revision ID: a1b2c3d4e5f6
Revises: 9e8f1a2b3c4d
Create Date: 2026-09-29

Renomeia a coluna de limite de orçamento para `amount_limit`.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "9e8f1a2b3c4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names() -> set[str]:
    """Colunas atuais de budgets (o schema pode vir do baseline ou do create_all)."""
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns("budgets")}


def upgrade() -> None:
    # ALTER TABLE ... RENAME COLUMN atualiza também o CHECK (amount > 0) para
    # (amount_limit > 0). O modo batch do Alembic no SQLite não faz isso e
    # gerava DDL inválida ao recriar a tabela temporária.
    columns = _column_names()
    if "amount" in columns and "amount_limit" not in columns:
        op.execute(sa.text('ALTER TABLE budgets RENAME COLUMN "amount" TO "amount_limit"'))


def downgrade() -> None:
    columns = _column_names()
    if "amount_limit" in columns and "amount" not in columns:
        op.execute(sa.text('ALTER TABLE budgets RENAME COLUMN "amount_limit" TO "amount"'))
