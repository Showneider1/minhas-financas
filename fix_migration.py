"""Correção da migration f1a5b599f589_p2_vaults.py — remove linhas inválidas para SQLite."""

content = '''"""p2 vaults

Revision ID: f1a5b599f589
Revises: c3d4e5f6a7b8
Create Date: 2026-10-03

Removidos drop_constraint(create_foreign_key)(None) incompatíveis com SQLite.
"""\n
# revision identifiers\nrevision = "f1a5b599f589"\ndown_revision = "c3d4e5f6a7b8"\nbranch_labels = None\ndepends_on = None\n\n\ndef upgrade() -> None:\n    # Create vaults table — SQLite-compatible, sem drop_foreign_key\n    op.create_table(\n        "vaults",\n        sa.Column("id", sa.Integer(), nullable=False),\n        sa.Column("user_id", sa.Integer(), nullable=False),\n        sa.Column("name", sa.String(length=100)),\n        sa.Column("target_amount", sa.Numeric(precision=12, scale=2)),\n        sa.Column("saved_amount", sa.Numeric(precision=12, scale=2)),\n        sa.Column("deadline", sa.Date(), nullable=True),\n        sa.Column("color", sa.String(length=7), nullable=True),\n        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),\n        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),\n        sa.CheckConstraint("saved_amount >= 0", name="ck_vault_saved_non_negative"),\n        op.FK.foreign_key(user_id="users.id", ondelete="CASCADE"),\n        primary_key=[sa.Column("id")],\n    )\n    # Index\n    with batch_op.batch_alter_table("vaults", schema=None) as batch_op:\n        batch_op.create_index(batch_op.f("ix_vaults_id"), ["id"], unique=False)\n\n\ndef downgrade() -> None:\n    with batch_op.batch_alter_table("vaults", schema=None) as batch_op:\n        batch_op.drop_index(batch_op.f("ix_vaults_id"))\n    op.drop_table("vaults")
'''

with open("alembic/versions/f1a5b599f589_p2_vaults.py", "w") as f:
    f.write(content)
