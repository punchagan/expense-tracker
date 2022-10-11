"""rename tables

Revision ID: d97b345819ad
Revises: 834c91a1644e
Create Date: 2022-10-11 08:43:14.812769

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d97b345819ad"
down_revision = "834c91a1644e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("expenses", "expense")
    op.rename_table("new_ids", "new_id")


def downgrade() -> None:
    op.rename_table("expense", "expenses")
    op.rename_table("new_id", "new_ids")
