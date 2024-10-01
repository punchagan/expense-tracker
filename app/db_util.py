import os
import sqlite3
import tempfile
from collections import Counter
from dataclasses import fields
from pathlib import Path
from typing import cast

from sqlalchemy import create_engine, or_, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Query, sessionmaker
from sqlalchemy.orm.session import Session

from app.data import CATEGORIES, create_categories, create_tags
from app.model import Category, Expense, Tag
from app.scrapers import ALL_SCRAPERS
from app.util import DATA_REPO_PATH

ROOT = Path(__file__).parent.parent
DB_NAME = os.getenv("EXPENSES_DB", "expenses.db")
DB_PATH = ROOT.joinpath(DB_NAME)


def category_names_lookup() -> dict[str, int]:
    session = get_sqlalchemy_session()
    categories = session.query(Category).all()
    return {str(cat.name).lower(): cast(int, cat.id) for cat in categories}


def counterparty_names_lookup() -> dict[tuple[str, str], str]:
    engine = get_db_engine()
    with engine.connect() as conn:
        names = conn.execute(
            text("SELECT source, counterparty_name_p, counterparty_name FROM expense")
        ).fetchall()
    lookup: dict[tuple[str, str], list[str]] = {}
    for source, parsed_name, name in names:
        if not (parsed_name and parsed_name != name):
            continue
        key = (source, parsed_name)
        value = lookup.setdefault(key, [])
        value.append(name)

    return {key: Counter(value).most_common(1)[0][0] for key, value in lookup.items()}


def ensure_categories_created() -> None:
    session = get_sqlalchemy_session()
    return create_categories(session, get_config_categories())


def ensure_tags_created() -> None:
    session = get_sqlalchemy_session()
    try:
        from conf import TAGS

        tags = TAGS
    except ImportError:
        tags = []
    return create_tags(session, tags)


def get_config_categories() -> list[str]:
    try:
        from conf import EXTRA_CATEGORIES

        categories = CATEGORIES + EXTRA_CATEGORIES
    except ImportError:
        categories = CATEGORIES
    return categories


def get_db_url() -> str:
    return f"sqlite:///{DB_PATH}"


def get_db_engine() -> Engine:
    return create_engine(get_db_url())


def get_sqlalchemy_session() -> Session:
    engine = get_db_engine()
    return sessionmaker(bind=engine)()


def parse_details_for_expenses(expenses: list[Expense] | Query[Expense], n_debug: int = 0) -> None:
    """Parse details for an expense object and update other fields.

    NOTE: This function could potentially be called on old data. Try not to
    clobber fields which may have been hand edited...

    """
    categories = category_names_lookup()
    counterparty_lookup = counterparty_names_lookup()
    examples = []
    for i, expense in enumerate(expenses):
        source_cls = ALL_SCRAPERS[str(expense.source)]
        transaction = source_cls.parse_details(expense)

        # Copy attributes from parsed Transaction dataclass to Expense object
        attrs = {f.name: f.name for f in fields(transaction)}
        attrs["counterparty_name_p"] = "counterparty_name"
        attrs["counterparty_bank_p"] = "counterparty_bank"
        for expense_attr, transaction_attr in attrs.items():
            setattr(expense, expense_attr, getattr(transaction, transaction_attr))

        # Change counterparty_name to most frequently used name on similar transactions
        name_p = str(expense.counterparty_name_p)
        lookup_key = (str(expense.source) or "", name_p or "")
        lookup_value = counterparty_lookup.get(lookup_key)
        if name_p and lookup_value:
            expense.counterparty_name = lookup_value

        # Set category id if category_name or remarks exactly match a category id.
        key = (expense.category is not None and str(expense.category.name).strip().lower()) or (
            expense.remarks is not None and expense.remarks.strip().lower() or ""
        )
        expense.category_id = categories.get(key, expense.category_id)

        if i < n_debug:
            examples.append(expense)

    for expense in examples:
        print(expense)
        print("#" * 40)


def update_similar_counterparty_names(session: Session, expense: Expense, name: str) -> None:
    expenses = session.query(Expense).filter(
        Expense.counterparty_name_p == expense.counterparty_name_p,
        Expense.counterparty_name == expense.counterparty_name,
        Expense.source == expense.source,
    )
    expenses.update({"counterparty_name": name}, synchronize_session=False)


def update_similar_counterparty_categories(
    session: Session,
    expense: Expense,
    category_name: str | None,
    all_categories: dict[int, Category],
) -> None:
    name = expense.counterparty_name
    expenses = session.query(Expense).where(
        or_(
            Expense.counterparty_name == name,
            Expense.parent == expense.id,
            Expense.id == expense.parent,
        )
    )
    name_map = {str(cat.name): cat.id for cat in all_categories.values()}
    category_id = name_map[category_name] if category_name is not None else None
    expenses.update({"category_id": category_id}, synchronize_session=False)


def set_tags_value(expense: Expense, tag: str | None, all_tags: dict[int, Tag]) -> None:
    old_tags = {tag.id: tag for tag in expense.tags}
    old_ids = set(old_tags)

    names_map = {str(tag.name): tag.id for tag in all_tags.values()}
    tag_id = names_map[tag] if tag else None
    new_ids = {tag_id} if tag else set()

    removed = old_ids - new_ids
    for old_id, old_tag in old_tags.items():
        if old_id in removed:
            expense.tags.remove(old_tag)

    added = new_ids - old_ids
    for tag_id in added:
        expense.tags.append(all_tags[cast(int, tag_id)])


def dump_db_to_csv(path: Path) -> None:
    engine: Engine = get_db_engine()
    with engine.connect() as conn, path.open("w") as f:
        sqlite_conn = cast(sqlite3.Connection, conn.connection)
        for line in sqlite_conn.iterdump():
            f.write(f"{line}\n")
    print(f"Dumped database to {path}")


def load_db_from_csv(db_path: Path, db_dump_path: Path) -> None:
    print(f"Loading DB from {db_dump_path}")

    engine: Engine = create_engine(f"sqlite:///{db_path}")

    with engine.connect() as conn:
        with db_dump_path.open("r") as f:
            sql: str = f.read()
        statements = sql.split(";\n")
        for statement in statements:
            conn.execute(text(statement))
        conn.commit()


def sync_db_with_data_repo() -> None:
    db_path: Path = Path(DB_PATH)
    repo_path: Path = DATA_REPO_PATH
    db_dump: Path = repo_path.joinpath("db.csv")

    if not db_path.exists() and not db_dump.exists():
        raise RuntimeError("Panic! No DB or DB dump found!")

    if not db_path.exists():
        load_db_from_csv(db_path, db_dump)
        return

    db_last_modified: float = db_path.stat().st_mtime
    dump_last_modified: float = db_dump.stat().st_mtime if db_dump.exists() else 0

    if db_last_modified > dump_last_modified:
        print("Database is newer than database dump")
        dump_db_to_csv(db_dump)

    elif dump_last_modified > db_last_modified:
        print("Database dump is newer than database")

        with tempfile.NamedTemporaryFile() as f:
            dump_db_to_csv(Path(f.name))
            temp_dump_text: str = Path(f.name).read_text()

        if db_dump.read_text() != temp_dump_text:
            print("Database dump has changed since last update")

            temp_db_path: Path = Path(tempfile.mkstemp(suffix=".sqlite")[1])
            load_db_from_csv(temp_db_path, db_dump)
            Path(DB_PATH).rename(DB_PATH.with_suffix(".bak"))
            temp_db_path.rename(DB_PATH)
            print(f"Replaced {DB_PATH} with the updated database")

        else:
            print("Database dump has not changed since last update")
            db_dump.touch()
            Path(DB_PATH).touch()

    else:
        print("The Database and the database dump are in sync")
