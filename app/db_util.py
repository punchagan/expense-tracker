import os
import re
import sys
import tempfile
from collections import Counter
from dataclasses import fields
from pathlib import Path

from sqlalchemy import create_engine, or_, text
from sqlalchemy.orm import sessionmaker

from app.data import CATEGORIES, create_categories, create_tags, get_country_data
from app.lib.git_manager import GitManager, get_repo_path
from app.model import Category, Expense
from app.scrapers import ALL_SCRAPERS

ROOT = Path(__file__).parent.parent
DB_NAME = os.getenv("EXPENSES_DB", "expenses.db")
DB_PATH = ROOT.joinpath(DB_NAME)


def category_names_lookup():
    session = get_sqlalchemy_session()
    categories = session.query(Category).all()
    return {cat.name.lower(): cat.id for cat in categories}


def counterparty_names_lookup():
    engine = get_db_engine()
    with engine.connect() as conn:
        names = conn.execute(
            text("SELECT source, counterparty_name_p, counterparty_name FROM expense")
        ).fetchall()
    lookup = {}
    for source, parsed_name, name in names:
        if not (parsed_name and parsed_name != name):
            continue
        key = (source, parsed_name)
        value = lookup.setdefault(key, [])
        value.append(name)

    return {key: Counter(value).most_common(1)[0][0] for key, value in lookup.items()}


def ensure_categories_created():
    session = get_sqlalchemy_session()
    return create_categories(session, get_config_categories())


def ensure_tags_created():
    session = get_sqlalchemy_session()
    git_manager = GitManager()
    try:
        path = str(git_manager.repo_path)
        if path not in sys.path:
            sys.path.insert(1, path)

        from conf import TAGS

        tags = TAGS
    except ImportError:
        tags = []
    return create_tags(session, tags)


def get_config_categories():
    git_manager = GitManager()
    try:
        path = str(git_manager.repo_path)
        if path not in sys.path:
            sys.path.insert(1, path)

        from conf import EXTRA_CATEGORIES

        categories = CATEGORIES + EXTRA_CATEGORIES
    except ImportError:
        categories = CATEGORIES
    return categories


def get_db_url():
    return f"sqlite:///{DB_PATH}"


def get_db_engine():
    return create_engine(get_db_url())


def get_sqlalchemy_session():
    engine = get_db_engine()
    return sessionmaker(bind=engine)()


def parse_details_for_expenses(expenses, n_debug=0):
    """Parse details for an expense object and update other fields.

    NOTE: This function could potentially be called on old data. Try not to
    clobber fields which may have been hand edited...

    """
    country, cities = get_country_data()
    country = re.compile(f",* ({'|'.join(country.values())})$", flags=re.IGNORECASE)
    cities = re.compile(f",* ({'|'.join(cities)})$", flags=re.IGNORECASE)
    categories = category_names_lookup()
    counterparty_lookup = counterparty_names_lookup()
    examples = []
    for i, expense in enumerate(expenses):
        source_cls = ALL_SCRAPERS[expense.source]

        # Parse details of an expense into a transaction object
        transaction = source_cls.parse_details(expense, country, cities)

        # Copy attributes from parsed Transaction dataclass to Expense object
        attrs = {f.name: f.name for f in fields(transaction)}
        attrs["counterparty_name_p"] = "counterparty_name"
        attrs["counterparty_bank_p"] = "counterparty_bank"
        for expense_attr, transaction_attr in attrs.items():
            setattr(expense, expense_attr, getattr(transaction, transaction_attr))

        # Change counterparty_name to most frequently used name on similar transactions
        name_p = expense.counterparty_name_p
        lookup_key = (expense.source, name_p)
        lookup_value = counterparty_lookup.get(lookup_key)
        if name_p and lookup_value:
            expense.counterparty_name = lookup_value

        # Set category id if category_name or remarks exactly match a category id.
        key = expense.category_name.strip().lower() or expense.remarks.strip().lower()
        expense.category_id = categories.get(key, expense.category_id)

        if i < n_debug:
            examples.append(expense)

    for expense in examples:
        print(expense)
        print("#" * 40)


def update_similar_counterparty_names(session, expense, name):
    expenses = session.query(Expense).filter(
        Expense.counterparty_name_p == expense.counterparty_name_p,
        Expense.counterparty_name == expense.counterparty_name,
        Expense.source == expense.source,
    )
    expenses.update({"counterparty_name": name}, synchronize_session=False)


def update_similar_counterparty_categories(session, expense, category_name, all_categories):
    name = expense.counterparty_name
    expenses = session.query(Expense).where(
        or_(
            Expense.counterparty_name == name,
            Expense.parent == expense.id,
            Expense.id == expense.parent,
        )
    )
    name_map = {cat.name: cat.id for cat in all_categories.values()}
    category_id = name_map[category_name] if category_name is not None else None
    expenses.update({"category_id": category_id}, synchronize_session=False)


def set_tags_value(expense, tag, all_tags):
    old_tags = {tag.id: tag for tag in expense.tags}
    old_ids = set(old_tags)

    names_map = {tag.name: tag.id for tag in all_tags.values()}
    tag_id = names_map[tag] if tag else None
    new_ids = set([tag_id]) if tag else set()

    removed = old_ids - new_ids
    for old_id, tag in old_tags.items():
        if old_id in removed:
            expense.tags.remove(tag)

    added = new_ids - old_ids
    for tag_id in added:
        expense.tags.append(all_tags[tag_id])


def dump_db_to_csv(path):
    # SQLAlchemy equivalent of "sqlite3 $EXPENSES_DB .dump"
    engine = get_db_engine()
    with engine.connect() as conn:
        with path.open("w") as f:
            for line in conn.connection.iterdump():
                f.write(f"{line}\n")
    print(f"Dumped database to {path}")


def load_db_from_csv(db_path, db_dump_path):
    # SQLAlchemy equivalent of "sqlite3 $EXPENSES_DB < db.csv"
    print(f"Loading DB from {db_dump_path}")

    engine = create_engine(f"sqlite:///{db_path}")

    # Load the SQL dump into the temporary database
    with engine.connect() as conn:
        with db_dump_path.open("r") as f:
            sql = f.read()
        statements = sql.split(";\n")
        for statement in statements:
            conn.execute(text(statement))
        conn.commit()


def sync_db_with_data_repo():
    db_path = Path(DB_PATH)
    repo_path = get_repo_path()
    db_dump = repo_path.joinpath("db.csv")

    if not db_path.exists() and not db_dump.exists():
        raise RuntimeError("Panic! No DB or DB dump found!")

    if not db_path.exists():
        load_db_from_csv(db_path, db_dump)
        return

    db_last_modified = db_path.stat().st_mtime
    dump_last_modified = db_dump.stat().st_mtime if db_dump.exists() else 0

    if db_last_modified > dump_last_modified:
        print("Database is newer than database dump")
        # Update db.csv with database data
        dump_db_to_csv(db_dump)

    elif dump_last_modified > db_last_modified:
        print("Database dump is newer than database")

        # Check if the current database dump is different from saved dump
        # and update database with db.csv data if needed
        with tempfile.NamedTemporaryFile() as f:
            dump_db_to_csv(Path(f.name))
            temp_dump_text = Path(f.name).read_text()

        if db_dump.read_text() != temp_dump_text:
            print("Database dump has changed since last update")

            # Load db_dump to temporary DB
            temp_db_path = Path(tempfile.mkstemp(suffix=".sqlite"))
            load_db_from_csv(temp_db_path, db_dump)
            # Backup the current DB and copy the temporary DB over the existing one
            Path(DB_PATH).rename(DB_PATH.with_suffix(".bak"))
            temp_db_path.rename(DB_PATH)
            print(f"Replaced {DB_PATH} with the updated database")

        else:
            print("Database dump has not changed since last update")
            # Touching both files to update their modified time
            db_dump.touch()
            Path(DB_PATH).touch()

    else:
        print("The Database and the database dump are in sync")
