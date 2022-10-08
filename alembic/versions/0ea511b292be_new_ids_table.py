"""new ids table

Revision ID: 0ea511b292be
Revises: c97322f9bec0
Create Date: 2022-10-08 17:35:46.459811

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0ea511b292be'
down_revision = 'c97322f9bec0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('new_ids',
    sa.Column('id', sa.String(length=40), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('new_ids')
    # ### end Alembic commands ###
