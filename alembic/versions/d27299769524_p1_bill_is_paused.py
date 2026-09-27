"""p1 bill is_paused (pausa sem cancelar recorrência)

Revision ID: d27299769524
Revises: 916651f2e591
Create Date: 2026-09-27

Aditiva e segura: só ADD COLUMN (existing rows → False via server_default).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd27299769524'
down_revision: Union[str, None] = '916651f2e591'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("scheduled_bills", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_paused",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("scheduled_bills", schema=None) as batch_op:
        batch_op.drop_column("is_paused")
