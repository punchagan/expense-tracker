#!/usr/bin/env python

# Standard libs
from hashlib import sha1
from pathlib import Path
import sys

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 3rd party libs
import pandas as pd
from sqlalchemy import create_engine, exc

# Local
from app.util import DB_NAME, get_db_url


AXIS_COLUMNS = {
    "date": "Tran Date",
    "details": "PARTICULARS",
    "credit": "CR",
    "debit": "DR",
    "amount": None,
}

AXIS_CC_COLUMNS = {
    "date": "Transaction Date",
    "details": "Transaction Details",
    "credit": "CR",
    "debit": "DR",
    "amount": "Amount in INR",
}

SBI_COLUMNS = {
    "date": "Txn Date",
    "details": "Description",
    "credit": "Credit",
    "debit": "Debit",
    "amount": None,
}

HEADERS = [AXIS_CC_COLUMNS, AXIS_COLUMNS, SBI_COLUMNS]


def get_transformed_row(x):
    """Transform a parsed row into a row to be saved in the DB."""
    columns = ["id", "date", "details", "amount"]
    x = x.fillna(0)

    for header_type in HEADERS:
        if header_type["date"] in x.index:
            break
    else:
        raise RuntimeError("Unknown CSV type")

    date = x[header_type["date"]]
    details = x[header_type["details"]]

    amount_h, credit_h, debit_h = (
        header_type["amount"],
        header_type["credit"],
        header_type["debit"],
    )
    amount = x[amount_h] if amount_h else x[debit_h] - x[credit_h]
    hash_text = f"{details}-{date}-{amount}"
    sha = sha1(hash_text.encode("utf8")).hexdigest()
    return pd.Series([sha, date, details, amount], index=columns)


def get_db_engine():
    return create_engine(get_db_url())


def parse_data(path, catch_phrase):
    """Parses the data in a given `path` and dumps to `DB_NAME`."""
    transaction_date = catch_phrase
    data = (
        pd.read_csv(
            path,
            parse_dates=[transaction_date],
            dayfirst=True,
            dtype={
                "Amount in INR": "float64",
                "DR": "float64",
                "CR": "float64",
                "Debit": "float64",
                "Credit": "float64",
            },
            thousands=",",
            na_values=[" "],
        )
        .fillna(0)
        .sort_values(by=[transaction_date], ignore_index=True)
    )
    data = data.apply(get_transformed_row, axis=1)

    engine = get_db_engine()
    data["id"].to_sql("new_ids", engine, if_exists="append", index=False)
    try:
        new_ids = engine.execute(
            "SELECT id FROM new_ids WHERE id NOT IN (SELECT id FROM expenses)"
        ).fetchall()
        new_ids = [id_ for (id_,) in new_ids]
        engine.execute("DELETE FROM new_ids")
    except exc.OperationalError:
        new_ids = list(data["id"])

    # Select only IDs not already in the DB.
    data = data[data["id"].isin(new_ids)]
    rows = data.to_sql("expenses", engine, if_exists="append", index=False)
    print(f"Wrote {rows} rows from {path} to the {engine.url}")


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Path to the file to be parsed")
    parser.add_argument(
        "--catch-phrase",
        default="Transaction Date",
        help="Phrase in file to identify CSV header",
    )

    args = parser.parse_args()
    engine = get_db_engine()
    try:
        engine.execute("SELECT * FROM expenses").fetchone()
        engine.execute("SELECT * FROM new_ids").fetchone()
    except exc.OperationalError:
        sys.exit(f"Run `alembic upgrade head` before running {sys.argv[0]}.")
    parse_data(args.path, args.catch_phrase)
