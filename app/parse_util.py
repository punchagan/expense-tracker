# Standard libs
from __future__ import annotations

from hashlib import sha1
from pathlib import Path
from typing import Any, cast

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
from app.scrapers.base import Source


def get_transformed_row(
    x: pd.Series[Any], header_columns: dict[str, str], filename: str
) -> pd.Series[Any]:
    """Transform a parsed row into a row to be saved in the DB."""
    columns = ["id", "date", "details", "amount", "source_file", "source_line"]
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
    v = x[list(filter(None, amount_columns))].infer_objects().fillna(0)
    amount = v[amount_h] if amount_h else v[debit_h] - v[credit_h]
    hash_text = f"{filename}-{x.name}-{details}-{date}-{amount}"
    sha = sha1(hash_text.encode("utf8")).hexdigest()  # noqa: S324
    return pd.Series([sha, date, details, amount, filename, x.name], index=columns)


def parse_data(path: Path, source_cls: type[Source]) -> None:
    """Parses the data in a given `path` and dumps to `DB_NAME`."""
    print(f"Parsing {path} using '{source_cls.name}' scraper...")
    date_column = cast(str, source_cls.columns["date"])
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
        expenses = [
            Expense(**{str(key): value for key, value in d.items()})
            for d in data.to_dict("records")
        ]
        parse_details_for_expenses(expenses)
        session = get_sqlalchemy_session()
        session.add_all(expenses)
        session.commit()
        rows = len(expenses)
    else:
        rows = len(data)
    print(f"Wrote {rows} rows from {path} to the {engine.url}")
