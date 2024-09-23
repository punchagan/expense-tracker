"""add transaction, counterparty columns

Revision ID: 0a755389be4c
Revises: 4e45ce3ba587
Create Date: 2022-10-18 09:05:09.481140

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0a755389be4c"
down_revision = "4e45ce3ba587"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("expense", sa.Column("transaction_id", sa.String(length=20), nullable=True))
    op.add_column(
        "expense",
        sa.Column(
            "transaction_type",
            sa.String(length=10),
            server_default=sa.text("'Cash'"),
            nullable=False,
        ),
    )
    op.add_column("expense", sa.Column("counterparty_name", sa.String(length=100), nullable=True))
    op.add_column("expense", sa.Column("counterparty_name_p", sa.String(length=100), nullable=True))
    op.add_column("expense", sa.Column("counterparty_type", sa.String(length=20), nullable=True))
    op.add_column("expense", sa.Column("counterparty_bank", sa.String(length=100), nullable=True))
    op.add_column("expense", sa.Column("counterparty_bank_p", sa.String(length=100), nullable=True))
    op.add_column("expense", sa.Column("remarks", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("expense", "remarks")
    op.drop_column("expense", "counterparty_bank")
    op.drop_column("expense", "counterparty_type")
    op.drop_column("expense", "counterparty_name")
    op.drop_column("expense", "transaction_type")
    op.drop_column("expense", "transaction_id")
