import os
import re
from collections import Counter
from dataclasses import fields
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.data import CATEGORIES, create_categories, create_tags, get_country_data
from app.model import Category
from app.source import CSV_TYPES

ROOT = Path(__file__).parent.parent
DB_NAME = os.getenv("EXPENSES_DB", "expenses.db")
DB_PATH = ROOT.joinpath(DB_NAME)


def category_names_lookup():
    session = get_sqlalchemy_session()
    categories = session.query(Category).all()
    return {cat.name.lower(): cat.id for cat in categories}


def counterparty_names_lookup():
    engine = get_db_engine()
    with engine.connect() as conn:
        names = conn.execute(
            text("SELECT source, counterparty_name_p, counterparty_name FROM expense")
        ).fetchall()
    lookup = {}
    for source, parsed_name, name in names:
        if not (parsed_name and parsed_name != name):
            continue
        key = (source, parsed_name)
        value = lookup.setdefault(key, [])
        value.append(name)

    return {key: Counter(value).most_common(1)[0][0] for key, value in lookup.items()}


def ensure_categories_created():
    session = get_sqlalchemy_session()
    return create_categories(session, get_config_categories())


def ensure_tags_created():
    session = get_sqlalchemy_session()
    try:
        from conf import TAGS as tags
    except ImportError:
        tags = []
    return create_tags(session, tags)


def get_config_categories():
    try:
        from conf import EXTRA_CATEGORIES

        categories = CATEGORIES + EXTRA_CATEGORIES
    except ImportError:
        categories = CATEGORIES
    return categories


def get_db_url():
    return f"sqlite:///{DB_PATH}"


def get_db_engine():
    return create_engine(get_db_url())


def get_sqlalchemy_session():
    engine = get_db_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def parse_details_for_expenses(expenses, n_debug=0):
    """Parse details for an expense object and update other fields.

    NOTE: This function could potentially be called on old data. Try not to
    clobber fields which may have been hand edited...

    """
    country, cities = get_country_data()
    country = re.compile(f",* ({'|'.join(country.values())})$", flags=re.IGNORECASE)
    cities = re.compile(f",* ({'|'.join(cities)})$", flags=re.IGNORECASE)
    categories = category_names_lookup()
    counterparty_lookup = counterparty_names_lookup()
    examples = []
    for i, expense in enumerate(expenses):
        source_cls = CSV_TYPES[expense.source]

        # Parse details of an expense into a transaction object
        transaction = source_cls.parse_details(expense, country, cities)

        # Copy attributes from parsed Transaction dataclass to Expense object
        attrs = {f.name: f.name for f in fields(transaction)}
        attrs["counterparty_name_p"] = "counterparty_name"
        attrs["counterparty_bank_p"] = "counterparty_bank"
        for expense_attr, transaction_attr in attrs.items():
            setattr(expense, expense_attr, getattr(transaction, transaction_attr))

        # Change counterparty_name to most frequently used name on similar transactions
        name_p = expense.counterparty_name_p
        lookup_key = (expense.source, name_p)
        lookup_value = counterparty_lookup.get(lookup_key)
        if name_p and lookup_value:
            expense.counterparty_name = lookup_value

        # Set category id if category_name or remarks exactly match a category id.
        key = expense.category_name.strip().lower() or expense.remarks.strip().lower()
        expense.category_id = categories.get(key, expense.category_id)

        if i < n_debug:
            examples.append(expense)

    for expense in examples:
        print(expense)
        print("#" * 40)
