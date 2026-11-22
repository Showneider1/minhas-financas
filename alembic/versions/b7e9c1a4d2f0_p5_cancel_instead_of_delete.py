"""p5 cancel instead of delete

Revision ID: b7e9c1a4d2f0
Revises: f1a5b599f589
Create Date: 2026-11-22

Estorno como transição de estado para CANCELLED (sem lançamento
compensatório), preservando o histórico.

ATENÇÃO (downgrade): reverte apenas o esquema (índices e colunas). O
downgrade NÃO recupera o histórico cancelado — as informações de
cancelled_at / cancelled_by / cancellation_reason e o status CANCELLED
das linhas já estornadas são descartadas junto com as colunas.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b7e9c1a4d2f0"
down_revision: Union[str, None] = "f1a5b599f589"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ADD COLUMN + CREATE INDEX (sem RENAME): seguro no modo batch do SQLite,
    # inclusive com os CHECK constraints do baseline.
    #
    # As FKs de cancelled_by são NOMEADAS de propósito: o add_column do Alembic
    # emite um add_constraint implícito, e no SQLite uma FK sem nome faz o modo
    # batch falhar com "Constraint must have a name" (o mesmo padrão já usado
    # em 7d8e9f0a1b2c_p1_credit_cards.py). O recreate resultante preserva os
    # dados — verificado em upgrade/downgrade round-trip com linhas preenchidas.
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column(
                "cancelled_by",
                sa.Integer,
                sa.ForeignKey(
                    "users.id", ondelete="SET NULL", name="fk_transactions_cancelled_by_users"
                ),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("cancellation_reason", sa.String(length=255), nullable=True))
        batch_op.create_index(
            "ix_transactions_user_status",
            ["user_id", "status"],
            unique=False,
        )

    with op.batch_alter_table("investment_operations", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "status",
                sa.Enum("ACTIVE", "CANCELLED", name="investmentoperationstatus", native_enum=False),
                nullable=False,
                server_default="ACTIVE",
            )
        )
        batch_op.add_column(sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column(
                "cancelled_by",
                sa.Integer,
                sa.ForeignKey(
                    "users.id",
                    ondelete="SET NULL",
                    name="fk_investment_ops_cancelled_by_users",
                ),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("cancellation_reason", sa.String(length=255), nullable=True))
        batch_op.create_index(
            "ix_investment_ops_asset_status_date",
            ["asset_id", "status", "date"],
            unique=False,
        )


def downgrade() -> None:
    # Ordem inversa do upgrade. Não recupera o histórico cancelado.
    with op.batch_alter_table("investment_operations", schema=None) as batch_op:
        batch_op.drop_index("ix_investment_ops_asset_status_date")
        batch_op.drop_column("cancellation_reason")
        batch_op.drop_column("cancelled_by")
        batch_op.drop_column("cancelled_at")
        batch_op.drop_column("status")

    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.drop_index("ix_transactions_user_status")
        batch_op.drop_column("cancellation_reason")
        batch_op.drop_column("cancelled_by")
        batch_op.drop_column("cancelled_at")
