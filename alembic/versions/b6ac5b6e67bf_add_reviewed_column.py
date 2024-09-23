"""add reviewed column

Revision ID: b6ac5b6e67bf
Revises: d4144ee20c0c
Create Date: 2022-10-30 16:50:43.576580

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "b6ac5b6e67bf"
down_revision = "d4144ee20c0c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("expense", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("reviewed", sa.Boolean(), server_default=sa.text("0"), nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("expense", schema=None) as batch_op:
        batch_op.drop_column("reviewed")
