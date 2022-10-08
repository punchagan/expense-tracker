"""initial-table

Revision ID: c97322f9bec0
Revises: 
Create Date: 2022-10-07 11:23:55.185469

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c97322f9bec0'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('expenses',
    sa.Column('id', sa.String(length=40), nullable=False),
    sa.Column('date', sa.DateTime(), nullable=False),
    sa.Column('details', sa.Text(), nullable=False),
    sa.Column('amount', sa.Float(asdecimal=True, decimal_return_scale=2), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('expenses')
    # ### end Alembic commands ###