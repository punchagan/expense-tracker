#!/usr/bin/env python

# Standard libs
from dataclasses import fields
from hashlib import sha1
from pathlib import Path
import re
import sys

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 3rd party libs
import pandas as pd
from sqlalchemy import exc

# Local
from app.db_util import get_db_engine, get_sqlalchemy_session, lookup_counterparty_names
from app.model import Expense
from app.source import CSV_TYPES
from app.util import get_country_data

# NOTE: Currently, hard-code India as the country of purchases
COUNTRY = "India"


def parse_old_data(commit=False, num_examples=10):
    """Parses "old" data in the DB using the appropriate parser."""
    session = get_sqlalchemy_session()
    engine = get_db_engine()
    lookup = lookup_counterparty_names(engine)
    # NOTE: The filter query expression could be a CLI argument? It's possible
    # to do this by implementing an API like the QuerySet Filter API in Django
    # and accepting the query as JSON argument. But, maynot be worth the
    # effort, as of now.
    expenses = session.query(Expense).filter(Expense.transaction_id == None)
    country, cities = get_country_data(COUNTRY)
    country = re.compile(f",* ({'|'.join(country.values())})$", flags=re.IGNORECASE)
    cities = re.compile(f",* ({'|'.join(cities)})$", flags=re.IGNORECASE)
    count = expenses.count()
    examples = []
    for i, expense in enumerate(expenses):
        source_cls = CSV_TYPES[expense.source]
        row = dict(details=expense.details)
        transaction = source_cls.parse_details(row, country, cities)
        attrs = {f.name: f.name for f in fields(transaction)}
        attrs["counterparty_name_p"] = "counterparty_name"
        attrs["counterparty_bank_p"] = "counterparty_bank"
        for expense_attr, transaction_attr in attrs.items():
            setattr(expense, expense_attr, getattr(transaction, transaction_attr))

        name_p = expense.counterparty_name_p
        lookup_key = (expense.source, name_p)
        lookup_value = lookup.get(lookup_key)
        if name_p and lookup_value:
            expense.counterparty_name = lookup_value

        if i < num_examples:
            examples.append(expense)

    for expense in examples:
        print(expense)
        print("#" * 40)
    print(f"Filtered {count} transactions to filter...")
    print(f"Showing {len(examples)} example transactions above")

    if commit:
        yes = input("Do you wish to commit the changes([n]/y)? ")
        if yes[0:1].lower() == "y":
            print(f"Commiting {count} changes!")
            session.commit()


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--commit", action="store_true", help="Commit the changes after confirmation"
    )
    parser.add_argument(
        "-n", "--num-examples", default=10, help="Number of examples to show", type=int
    )
    args = parser.parse_args()
    engine = get_db_engine()
    try:
        engine.execute("SELECT * FROM expense").fetchone()
    except exc.OperationalError:
        sys.exit(f"The DB has no old data!")
    parse_old_data(**dict(args._get_kwargs()))
