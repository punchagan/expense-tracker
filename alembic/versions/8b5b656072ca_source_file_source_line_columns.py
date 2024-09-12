"""source file source line columns

Revision ID: 8b5b656072ca
Revises: b6ac5b6e67bf
Create Date: 2024-09-13 18:02:00.009427

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8b5b656072ca"
down_revision = "b6ac5b6e67bf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add source_file and source_line columns to expense table
    op.add_column("expense", sa.Column("source_file", sa.String(length=100), nullable=True))
    op.add_column("expense", sa.Column("source_line", sa.Integer(), nullable=True))


def downgrade() -> None:
    # Remove source_file and source_line columns to expense table
    op.drop_column("expense", "source_file")
    op.drop_column("expense", "source_line")
