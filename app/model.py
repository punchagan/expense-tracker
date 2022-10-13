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
    categories = relationship(
        "Category", secondary="expense_category", backref="expenses"
    )
    source = sa.Column(
        sa.String(10), server_default=sa.sql.expression.literal(""), nullable=False
    )

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


expense_category_table = sa.Table(
    "expense_category",
    Base.metadata,
    sa.Column("expense_id", sa.ForeignKey("expense.id"), primary_key=True),
    sa.Column("category_id", sa.ForeignKey("category.id"), primary_key=True),
)
