import sqlalchemy as sa
from sqlalchemy.orm import declarative_base, relationship


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
    category_id = sa.Column(sa.Integer, sa.ForeignKey("category.id"))
    category = relationship("Category", backref="expenses")
    source = sa.Column(
        sa.String(10), server_default=sa.sql.expression.literal(""), nullable=False
    )
    transaction_id = sa.Column(sa.String(20), nullable=True)
    transaction_type = sa.Column(
        sa.String(10),
        default="Cash",
        server_default=sa.sql.expression.literal("Cash"),
        nullable=False,
    )
    counterparty_name = sa.Column(sa.String(100), nullable=True)
    counterparty_name_p = sa.Column(sa.String(100), nullable=True)
    counterparty_type = sa.Column(sa.String(20), nullable=True)
    counterparty_bank = sa.Column(sa.String(100), nullable=True)
    counterparty_bank_p = sa.Column(sa.String(100), nullable=True)
    remarks = sa.Column(sa.Text(), nullable=True)

    def __repr__(self):
        return f"Expense(id={self.id!r}, date={self.date!r}, amount={self.amount!r}, details={self.details!r}, ignore={self.ignore!r})"


class NewID(Base):
    __tablename__ = "new_id"
    id = sa.Column(sa.String(40), primary_key=True)

    def __repr__(self):
        return f"NewID(id={self.id!r})"


class Category(Base):
    __tablename__ = "category"
    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(40))

    def __repr__(self):
        return f"Category(id={self.id!r}, name={self.name!r})"
