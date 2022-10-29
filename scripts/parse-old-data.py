#!/usr/bin/env python

# Standard libs
from pathlib import Path
import sys

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 3rd party libs
import pandas as pd
from sqlalchemy import exc

# Local
from app.db_util import (
    get_db_engine,
    get_sqlalchemy_session,
    parse_details_for_expenses,
)
from app.model import Expense


def parse_old_data(commit=False, num_examples=10):
    """Parses "old" data in the DB using the appropriate parser."""
    session = get_sqlalchemy_session()
    # NOTE: The filter query expression could be a CLI argument? It's possible
    # to do this by implementing an API like the QuerySet Filter API in Django
    # and accepting the query as JSON argument. But, maynot be worth the
    # effort, as of now.
    expenses = session.query(Expense).filter(Expense.transaction_id == None)
    count = expenses.count()
    parse_details_for_expenses(expenses, n_debug=num_examples)
    n = min(num_examples, count)
    print(f"Filtered {count} transactions to filter...")
    print(f"Showing {n} example transactions above")
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
