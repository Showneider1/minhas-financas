"""p2 assets target_allocation_pct

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-10-01

Adiciona a meta de alocação (`target_allocation_pct`, Decimal(5,2)) usada pelo
módulo de Rebalanceamento Buy & Hold. Default 0 mantém compatibilidade com os
ativos já cadastrados (estratégia ainda não definida).

O limite de soma <= 100% é validado em código (InvestmentService), pois
depende de agregação sobre outras linhas da mesma tabela do usuário.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "target_allocation_pct",
                sa.Numeric(5, 2),
                nullable=False,
                server_default="0",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("assets", schema=None) as batch_op:
        batch_op.drop_column("target_allocation_pct")
