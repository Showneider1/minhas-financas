"""p1 investment 18_8 (cotas fracionárias até 8 casas)

Revision ID: 92ca3cae3903
Revises: d27299769524
Create Date: 2026-09-27

Altera quantity/price_per_unit/fees/total_amount para NUMERIC(18,8).
Aditiva na prática (tabelas vazias no dev); batch mode p/ SQLite.
Cobre origem FLOAT (SQLite legado) e NUMERIC(14,4) (baseline Postgres).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '92ca3cae3903'
down_revision: Union[str, None] = 'd27299769524'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_QTY = sa.Numeric(18, 8)


def upgrade() -> None:
    with op.batch_alter_table("investment_operations", schema=None) as batch_op:
        batch_op.alter_column("quantity", type_=_QTY, existing_nullable=False)
        batch_op.alter_column("price_per_unit", type_=_QTY, existing_nullable=False)
        batch_op.alter_column("fees", type_=_QTY, existing_nullable=True)
        batch_op.alter_column("total_amount", type_=_QTY, existing_nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("investment_operations", schema=None) as batch_op:
        batch_op.alter_column("quantity", type_=sa.Numeric(14, 4), existing_nullable=False)
        batch_op.alter_column("price_per_unit", type_=sa.Numeric(14, 4), existing_nullable=False)
        batch_op.alter_column("fees", type_=sa.Numeric(14, 4), existing_nullable=True)
        batch_op.alter_column("total_amount", type_=sa.Numeric(14, 4), existing_nullable=False)
