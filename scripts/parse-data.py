#!/usr/bin/env python

# Standard libs
import sys
from hashlib import sha1
from pathlib import Path

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 3rd party libs
import pandas as pd
from sqlalchemy import exc

# Local
from app.db_util import (
    ensure_categories_created,
    ensure_tags_created,
    get_db_engine,
    get_sqlalchemy_session,
    parse_details_for_expenses,
)
from app.model import Expense
from app.source import CSV_TYPES

# NOTE: Currently, hard-code India as the country of purchases
COUNTRY = "India"


def get_transformed_row(x, csv_type):
    """Transform a parsed row into a row to be saved in the DB."""
    columns = ["id", "date", "details", "amount"]
    x = x.fillna(0)

    header_columns = CSV_TYPES[csv_type].columns
    date = x[header_columns["date"]]
    details = x[header_columns["details"]]
    if isinstance(details, pd.Series):
        details = "/".join(details.str.strip())
    details = details.strip()
    amount_h, credit_h, debit_h = (
        header_columns["amount"],
        header_columns["credit"],
        header_columns["debit"],
    )
    amount = x[amount_h] if amount_h else x[debit_h] - x[credit_h]
    hash_text = f"{details}-{date}-{amount}"
    sha = sha1(hash_text.encode("utf8")).hexdigest()
    return pd.Series([sha, date, details, amount], index=columns)


def transform_data(data, csv_type, engine):
    source_cls = CSV_TYPES[csv_type]
    transactions = data.apply(
        source_cls.parse_details, axis=1, country=country, cities=cities
    ).apply(lambda x: pd.Series(x.__dict__))
    data = pd.concat([data, transactions], axis=1)
    data["counterparty_bank_p"] = data["counterparty_bank"]

    # Modify counterparty_name based on previously manually updated names
    data["counterparty_name_p"] = data["counterparty_name"]
    parsed_names = tuple(set(data["counterparty_name_p"]) - set([""]))
    if parsed_names:
        names = lookup_counterparty_names(engine)
        data["counterparty_name"] = data["counterparty_name"].apply(
            lambda x: names.get(x, x)
        )
    return data


def parse_data(path, csv_type):
    """Parses the data in a given `path` and dumps to `DB_NAME`."""
    source_cls = CSV_TYPES[csv_type]
    transaction_date = source_cls.columns["date"]
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
    data = data.apply(get_transformed_row, axis=1, csv_type=csv_type)

    engine = get_db_engine()
    data["id"].to_sql("new_id", engine, if_exists="append", index=False)
    try:
        new_ids = engine.execute(
            "SELECT id FROM new_id WHERE id NOT IN (SELECT id FROM expense)"
        ).fetchall()
        new_ids = [id_ for (id_,) in new_ids]
        engine.execute("DELETE FROM new_id")
    except exc.OperationalError:
        new_ids = list(data["id"])

    # Select only IDs not already in the DB.
    data = data[data["id"].isin(new_ids)]
    if not data.empty:
        data["source"] = csv_type
        expenses = [Expense(**d) for d in data.to_dict("records")]
        parse_details_for_expenses(expenses)
        session = get_sqlalchemy_session()
        session.add_all(expenses)
        session.commit()
        rows = len(expenses)
    else:
        rows = len(data)
    print(f"Wrote {rows} rows from {path} to the {engine.url}")


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Path to the file to be parsed")
    parser.add_argument(
        "--csv-type", default="axis", choices=CSV_TYPES.keys(), help="Type of CSV"
    )

    args = parser.parse_args()
    engine = get_db_engine()
    try:
        engine.execute("SELECT * FROM expense").fetchone()
        engine.execute("SELECT * FROM new_id").fetchone()
    except exc.OperationalError:
        sys.exit(f"Run `alembic upgrade head` before running {sys.argv[0]}.")

    ensure_categories_created()
    ensure_tags_created()
    parse_data(args.path, args.csv_type)
