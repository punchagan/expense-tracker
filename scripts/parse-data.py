#!/usr/bin/env python

# Standard libs
import csv
from hashlib import sha1
import io
from pathlib import Path
import sys

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 3rd party libs
from bs4 import BeautifulSoup
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
    if path.endswith(".html"):
        data = extract_csv_from_html(path)
    else:
        data = path

    csv = extract_csv(data, catch_phrase)
    transaction_date = catch_phrase
    data = (
        pd.read_csv(
            csv,
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


def extract_csv(path, catch_phrase="Transaction Date"):
    """Extact CSV part of a file, based on a catch phrase in the header."""

    if isinstance(path, io.StringIO):
        text = path.read().strip().splitlines()

    else:
        with open(path) as f:
            text = f.read().strip().splitlines()

    if not text:
        return io.StringIO("")

    start_line = None
    end_line = None

    for num, line in enumerate(text):
        # Set beginning of CSV if catch_phrase is found in a line
        if catch_phrase in line:
            start_line = num
        # Set end of CSV as the first empty line after the header
        elif start_line is not None and not line.strip():
            end_line = num
            break
        else:
            continue
    else:
        # If there's no empty line, continue until the end
        end_line = num + 1

    # Strip leading and trailing commas
    lines = [line.strip(",") for line in text[start_line:end_line]]
    return io.StringIO("\n".join(lines))


def extract_csv_from_html(htmlfile):
    """Converts html to a CSV."""
    with open(htmlfile) as f:
        soup = BeautifulSoup(f, "html.parser")
    table = soup.findAll("table")[1]
    rows = table.findAll("tr")
    csv_output = io.StringIO()
    csv_rows = [
        [cell.get_text().strip() for cell in row.findAll(["td", "th"])][2:-2]
        for row in rows
    ]
    writer = csv.writer(csv_output)
    writer.writerows(csv_rows)
    csv_output.seek(0)
    return csv_output


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
