"""p1 credit cards

Revision ID: 7d8e9f0a1b2c
Revises: 3f1a0c6b7d2e
Create Date: 2026-09-28

Aditiva: cria a tabela de cartões e vincula transações ao cartão.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7d8e9f0a1b2c"
down_revision: str | None = "3f1a0c6b7d2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "credit_cards",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("credit_limit", sa.Numeric(12, 2), nullable=False),
        sa.Column("closing_day", sa.Integer(), nullable=False),
        sa.Column("due_day", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", name="uq_credit_cards_account"),
    )
    op.create_index("ix_credit_cards_id", "credit_cards", ["id"], unique=False)
    op.create_index("ix_credit_cards_user_id", "credit_cards", ["user_id"], unique=False)
    op.create_index("ix_credit_cards_account_id", "credit_cards", ["account_id"], unique=False)

    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("credit_card_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_transactions_credit_card_id",
            "credit_cards",
            ["credit_card_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_transactions_credit_card_id",
            ["credit_card_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.drop_index("ix_transactions_credit_card_id", table_name="transactions")
        batch_op.drop_constraint("fk_transactions_credit_card_id", type_="foreignkey")
        batch_op.drop_column("credit_card_id")

    op.drop_index("ix_credit_cards_account_id", table_name="credit_cards")
    op.drop_index("ix_credit_cards_user_id", table_name="credit_cards")
    op.drop_index("ix_credit_cards_id", table_name="credit_cards")
    op.drop_table("credit_cards")
