import sqlalchemy as sa
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class Expense(Base):
    __tablename__ = "expense"
    id = sa.Column(sa.String(40), primary_key=True)
    date = sa.Column(sa.DateTime(), nullable=False)
    details = sa.Column(sa.Text(), nullable=False)
    amount = sa.Column(sa.Float(asdecimal=True, decimal_return_scale=2), nullable=False)
    ignore = sa.Column(
        sa.Boolean(),
        nullable=False,
        default=False,
        server_default=sa.sql.expression.literal(False),
    )

    def __repr__(self):
        return f"Expense(id={self.id!r}, date={self.date!r}, amount={self.amount!r}, details={self.details!r}, ignore={self.ignore!r})"


class NewID(Base):
    __tablename__ = "new_id"
    id = sa.Column(sa.String(40), primary_key=True)

    def __repr__(self):
        return f"NewID(id={self.id!r})"
