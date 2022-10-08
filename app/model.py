import sqlalchemy as sa
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class Expense(Base):
    __tablename__ = "expenses"
    id = sa.Column(sa.String(40), primary_key=True)
    date = sa.Column(sa.DateTime(), nullable=False)
    details = sa.Column(sa.Text(), nullable=False)
    amount = sa.Column(sa.Float(asdecimal=True, decimal_return_scale=2), nullable=False)

    def __repr__(self):
        return f"Expense(date={self.date!r}, amount={self.amount!r} details={self.details!r})"


class NewID(Base):
    __tablename__ = "new_ids"
    id = sa.Column(sa.String(40), primary_key=True)

    def __repr__(self):
        return f"NewID(id={self.id!r})"
