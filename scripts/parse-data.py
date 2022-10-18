#!/usr/bin/env python

# Standard libs
from hashlib import sha1
from pathlib import Path
import re
import sys

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 3rd party libs
import pandas as pd
from sqlalchemy import create_engine, exc

# Local
from app.util import DB_NAME, get_country_data, get_db_url
from app.csv_types import CSV_TYPES

# NOTE: Currently, hard-code India as the country of purchases
COUNTRY = "India"


def get_transformed_row(x, csv_type):
    """Transform a parsed row into a row to be saved in the DB."""
    columns = ["id", "date", "details", "amount"]
    x = x.fillna(0)

    header_columns = CSV_TYPES[csv_type].columns
    date = x[header_columns["date"]]
    details = x[header_columns["details"]]
    amount_h, credit_h, debit_h = (
        header_columns["amount"],
        header_columns["credit"],
        header_columns["debit"],
    )
    amount = x[amount_h] if amount_h else x[debit_h] - x[credit_h]
    hash_text = f"{details}-{date}-{amount}"
    sha = sha1(hash_text.encode("utf8")).hexdigest()
    return pd.Series([sha, date, details, amount], index=columns)


def get_db_engine():
    return create_engine(get_db_url())


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
        country, cities = get_country_data(COUNTRY)
        country = re.compile(f",* ({'|'.join(country.values())})$", flags=re.IGNORECASE)
        cities = re.compile(f",* ({'|'.join(cities)})$", flags=re.IGNORECASE)
        transactions = data.apply(
            source_cls.parse_details, axis=1, country=country, cities=cities
        ).apply(lambda x: pd.Series(x.__dict__))
        data = pd.concat([data, transactions], axis=1)
        data["counterparty_name_p"] = data["counterparty_name"]
        data["counterparty_bank_p"] = data["counterparty_bank"]
        rows = data.to_sql("expense", engine, if_exists="append", index=False)
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
    parse_data(args.path, args.csv_type)
