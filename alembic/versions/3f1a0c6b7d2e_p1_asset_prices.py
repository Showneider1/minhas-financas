"""p1 asset prices cache (mark-to-market)

Revision ID: 3f1a0c6b7d2e
Revises: bfa4f83ffd32
Create Date: 2026-09-27

Aditiva: cria a tabela de cache de cotações sem alterar existentes.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "3f1a0c6b7d2e"
down_revision: Union[str, None] = "bfa4f83ffd32"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "asset_prices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=30), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("close_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ticker",
            "date",
            "provider",
            name="uq_asset_prices_ticker_date_provider",
        ),
    )
    op.create_index("ix_asset_prices_id", "asset_prices", ["id"], unique=False)
    op.create_index(
        "ix_asset_prices_ticker_date",
        "asset_prices",
        ["ticker", "date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_asset_prices_ticker_date", table_name="asset_prices")
    op.drop_index("ix_asset_prices_id", table_name="asset_prices")
    op.drop_table("asset_prices")
