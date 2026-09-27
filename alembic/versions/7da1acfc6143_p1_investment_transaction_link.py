"""p1 investment transaction link (liquidação no caixa)

Revision ID: 7da1acfc6143
Revises: 92ca3cae3903
Create Date: 2026-09-27

Vínculo 1:1 investment_operations.transaction_id -> transactions.id.
Aditiva e segura: coluna NULL + UNIQUE (tabelas vazias no dev).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7da1acfc6143'
down_revision: Union[str, None] = '92ca3cae3903'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("investment_operations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("transaction_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_investment_ops_transaction",
            "transactions", ["transaction_id"], ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_unique_constraint(
            "uq_investment_ops_transaction", ["transaction_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("investment_operations", schema=None) as batch_op:
        batch_op.drop_constraint("uq_investment_ops_transaction", type_="unique")
        batch_op.drop_constraint("fk_investment_ops_transaction", type_="foreignkey")
        batch_op.drop_column("transaction_id")
