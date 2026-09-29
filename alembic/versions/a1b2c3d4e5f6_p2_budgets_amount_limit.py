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


def upgrade() -> None:
    with op.batch_alter_table("budgets", schema=None) as batch_op:
        batch_op.alter_column(
            "amount",
            new_column_name="amount_limit",
            existing_type=sa.Numeric(12, 2),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("budgets", schema=None) as batch_op:
        batch_op.alter_column(
            "amount_limit",
            new_column_name="amount",
            existing_type=sa.Numeric(12, 2),
            existing_nullable=False,
        )
