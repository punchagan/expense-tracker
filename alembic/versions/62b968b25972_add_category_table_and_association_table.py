"""add category table and association table

Revision ID: 62b968b25972
Revises: d97b345819ad
Create Date: 2022-10-11 08:53:26.112567

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '62b968b25972'
down_revision = 'd97b345819ad'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('category',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=40), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('expense_category',
    sa.Column('expense_id', sa.String(length=40), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['category_id'], ['category.id'], ),
    sa.ForeignKeyConstraint(['expense_id'], ['expense.id'], ),
    sa.PrimaryKeyConstraint('expense_id', 'category_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('expense_category')
    op.drop_table('category')
    # ### end Alembic commands ###