"""add ignore column

Revision ID: 834c91a1644e
Revises: 0ea511b292be
Create Date: 2022-10-08 21:59:24.909679

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "834c91a1644e"
down_revision = "0ea511b292be"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "expenses",
        sa.Column("ignore", sa.Boolean(), server_default=sa.text("0"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("expenses", "ignore")
