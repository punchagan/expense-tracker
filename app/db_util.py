from collections import Counter
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).parent.parent
DB_NAME = os.getenv("EXPENSES_DB", "expenses.db")
DB_PATH = ROOT.joinpath(DB_NAME)


def get_db_url():
    return f"sqlite:///{DB_PATH}"


def get_db_engine():
    return create_engine(get_db_url())


def get_sqlalchemy_session():
    engine = get_db_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def lookup_counterparty_names(engine):
    names = engine.execute(
        "SELECT source, counterparty_name_p, counterparty_name FROM expense"
    ).fetchall()
    lookup = {}
    for source, parsed_name, name in names:
        if not (parsed_name and parsed_name != name):
            continue
        key = (source, parsed_name)
        value = lookup.setdefault(key, [])
        value.append(name)

    return {key: Counter(value).most_common(1)[0][0] for key, value in lookup.items()}
