from collections import Counter
from dataclasses import fields
import datetime
from logging.handlers import TimedRotatingFileHandler
import os
from pathlib import Path
import re
import shutil
from stat import ST_CTIME

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.data import get_country_data
from app.source import CSV_TYPES

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


def lookup_counterparty_names():
    engine = get_db_engine()
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


def backup_db(path=DB_PATH):
    """Make a copy of the DB if it is older than specified time.

    NOTE: TimedRotatingFileHandler uses the file's mtime to decide when to
    rollover. If a file is kept editing before the rollover interval expires,
    no backups would be created. We could try to use the ctime instead, but on
    Unix ctime is the same as mtime!!!

    """
    if not path.exists():
        return

    trfh = TimedRotatingFileHandler(
        path, delay=True, backupCount=30, when="d", interval=1
    )
    t = os.stat(path)[ST_CTIME]  # NOTE: ST_CTIME is the same as ST_MTIME on Unix
    trfh.rolloverAt = trfh.computeRollover(t)
    if not trfh.shouldRollover(record=None):
        return

    def namer(name):
        trfh._rotation_filename = name
        return name

    trfh.namer = namer

    trfh.doRollover()

    if not path.exists():
        # Copy the rolled over file with new created date
        dest = trfh._rotation_filename
        shutil.copy(dest, path)
        print(f"Backed up the DB to {dest}")

    return True


def parse_details_for_expenses(expenses, n_debug=0):
    country, cities = get_country_data()
    country = re.compile(f",* ({'|'.join(country.values())})$", flags=re.IGNORECASE)
    cities = re.compile(f",* ({'|'.join(cities)})$", flags=re.IGNORECASE)
    counterparty_lookup = lookup_counterparty_names()
    examples = []
    for i, expense in enumerate(expenses):
        source_cls = CSV_TYPES[expense.source]
        row = dict(details=expense.details)
        transaction = source_cls.parse_details(row, country, cities)
        attrs = {f.name: f.name for f in fields(transaction)}
        attrs["counterparty_name_p"] = "counterparty_name"
        attrs["counterparty_bank_p"] = "counterparty_bank"
        for expense_attr, transaction_attr in attrs.items():
            setattr(expense, expense_attr, getattr(transaction, transaction_attr))

        name_p = expense.counterparty_name_p
        lookup_key = (expense.source, name_p)
        lookup_value = counterparty_lookup.get(lookup_key)
        if name_p and lookup_value:
            expense.counterparty_name = lookup_value

        if i < n_debug:
            examples.append(expense)

    for expense in examples:
        print(expense)
        print("#" * 40)
