"""add source column

Revision ID: 4e45ce3ba587
Revises: 62b968b25972
Create Date: 2022-10-13 19:47:53.891453

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4e45ce3ba587'
down_revision = '62b968b25972'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('expense', sa.Column('source', sa.String(length=10), server_default=sa.text("('')"), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('expense', 'source')
    # ### end Alembic commands ###
