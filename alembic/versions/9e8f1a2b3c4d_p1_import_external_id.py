"""p1 import external id

Revision ID: 9e8f1a2b3c4d
Revises: 7d8e9f0a1b2c
Create Date: 2026-09-29

Aditiva: adiciona external_id (FITID) em transactions e índice por usuário.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "9e8f1a2b3c4d"
down_revision: Union[str, None] = "7d8e9f0a1b2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("external_id", sa.String(length=128), nullable=True))
        batch_op.create_index(
            "ix_transactions_external_id",
            ["external_id"],
            unique=False,
        )
        batch_op.create_unique_constraint(
            "uq_transactions_user_external_id",
            ["user_id", "external_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.drop_constraint("uq_transactions_user_external_id", type_="unique")
        batch_op.drop_index("ix_transactions_external_id", table_name="transactions")
        batch_op.drop_column("external_id")
