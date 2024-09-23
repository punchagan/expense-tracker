"""add parent column

Revision ID: d4144ee20c0c
Revises: 4b6790846b03
Create Date: 2022-10-22 20:50:02.624009

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d4144ee20c0c"
down_revision = "4b6790846b03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("expense", schema=None) as batch_op:
        batch_op.add_column(sa.Column("parent", sa.String(length=40), nullable=True))
        batch_op.create_foreign_key("expense-parent", "expense", ["parent"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("expense", schema=None) as batch_op:
        batch_op.drop_constraint("expense-parent", type_="foreignkey")
        batch_op.drop_column("parent")
