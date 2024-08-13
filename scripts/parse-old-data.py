#!/usr/bin/env python

"""Usage: python parse-old-data.py --commit -n <N> <FILTERS-JSON>

Script to reparse DB data, when improvements are made to the parser.

"""

# Standard libs
import json
import sys
from pathlib import Path

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 3rd party libs
from sqlalchemy import exc, text

# Local
from app.db_util import (
    get_db_engine,
    get_sqlalchemy_session,
    parse_details_for_expenses,
)
from app.model import Expense


def parse_old_data(filters, commit=False, num_examples=10):
    """Parses "old" data in the DB using the appropriate parser."""
    session = get_sqlalchemy_session()
    expenses = session.query(Expense).filter_by(**filters)
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
    # Add filters JSON positional argument
    parser.add_argument("filters", help="JSON argument for filters")
    parser.add_argument(
        "--commit", action="store_true", help="Commit the changes after confirmation"
    )
    parser.add_argument(
        "-n", "--num-examples", default=10, help="Number of examples to show", type=int
    )
    args = parser.parse_args()
    engine = get_db_engine()
    try:
        filters = json.loads(args.filters)
    except ValueError as e:
        print("Could not parse filters JSON")
        sys.exit(1)

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT * FROM expense")).fetchone()
    except exc.OperationalError:
        sys.exit(f"The DB has no old data!")
    parse_old_data(filters=filters, commit=args.commit, num_examples=args.num_examples)
