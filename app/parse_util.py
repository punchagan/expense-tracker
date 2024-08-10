# Standard libs
from hashlib import sha1
from pathlib import Path

# 3rd party libs
import pandas as pd
from sqlalchemy import exc, text

# Local
from app.db_util import (
    get_db_engine,
    get_sqlalchemy_session,
    parse_details_for_expenses,
)
from app.model import Expense
from app.source import CSV_TYPES


def get_transformed_row(x, csv_type, filename):
    """Transform a parsed row into a row to be saved in the DB."""
    columns = ["id", "date", "details", "amount"]

    header_columns = CSV_TYPES[csv_type].columns
    date = x[header_columns["date"]]
    details = x[header_columns["details"]]
    if isinstance(details, pd.Series):
        details = "/".join(details.fillna("").str.strip())
    details = details.strip()
    amount_columns = amount_h, credit_h, debit_h = (
        header_columns["amount"],
        header_columns["credit"],
        header_columns["debit"],
    )
    v = x[filter(None, amount_columns)].infer_objects(copy=False).fillna(0)
    amount = v[amount_h] if amount_h else v[debit_h] - v[credit_h]
    hash_text = f"{filename}-{x.name}-{details}-{date}-{amount}"
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
        data["counterparty_name"] = data["counterparty_name"].apply(lambda x: names.get(x, x))
    return data


def parse_data(path, csv_type):
    """Parses the data in a given `path` and dumps to `DB_NAME`."""
    source_cls = CSV_TYPES[csv_type]
    transaction_date = source_cls.columns["date"]
    data = pd.read_csv(
        path,
        parse_dates=[transaction_date],
        dayfirst=True,
        dtype=source_cls.dtypes,
        thousands=",",
        na_values=[" "],
    ).sort_values(by=[transaction_date], ignore_index=True)
    filename = Path(path).name
    data = data.apply(get_transformed_row, axis=1, csv_type=csv_type, filename=filename)

    engine = get_db_engine()
    data["id"].to_sql("new_id", engine, if_exists="append", index=False)
    try:
        with engine.connect() as conn:
            new_ids = conn.execute(
                text("SELECT id FROM new_id WHERE id NOT IN (SELECT id FROM expense)")
            ).fetchall()
            new_ids = [id_ for (id_,) in new_ids]
            conn.execute(text("DELETE FROM new_id"))
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
