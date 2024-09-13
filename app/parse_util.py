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


def get_transformed_row(x, header_columns, filename):
    """Transform a parsed row into a row to be saved in the DB."""
    columns = ["id", "date", "details", "amount"]
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


def parse_data(path, source_cls):
    """Parses the data in a given `path` and dumps to `DB_NAME`."""
    print(f"Parsing {path} using '{source_cls.name}' scraper...")
    date_column = source_cls.columns["date"]
    data = pd.read_csv(
        path,
        parse_dates=[date_column],
        dayfirst=True,
        dtype=source_cls.dtypes,
        thousands=",",
        na_values=[" "],
        date_format={date_column: source_cls.date_format},
    ).sort_values(by=[date_column], ignore_index=True)
    filename = Path(path).name
    columns = source_cls.columns
    data = data.apply(get_transformed_row, axis=1, header_columns=columns, filename=filename)

    engine = get_db_engine()
    data["id"].to_sql("new_id", engine, if_exists="append", index=False)
    try:
        with engine.connect() as conn:
            new_ids = conn.execute(
                text("SELECT id FROM new_id WHERE id NOT IN (SELECT id FROM expense)")
            ).fetchall()
            new_ids = [id_ for (id_,) in new_ids]
            conn.execute(text("DELETE FROM new_id"))
            conn.commit()
    except exc.OperationalError:
        new_ids = list(data["id"])

    # Select only IDs not already in the DB.
    data = data[data["id"].isin(new_ids)]
    if not data.empty:
        data["source"] = source_cls.name
        expenses = [Expense(**d) for d in data.to_dict("records")]
        parse_details_for_expenses(expenses)
        session = get_sqlalchemy_session()
        session.add_all(expenses)
        session.commit()
        rows = len(expenses)
    else:
        rows = len(data)
    print(f"Wrote {rows} rows from {path} to the {engine.url}")
