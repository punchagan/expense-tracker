#!/usr/bin/env python

# Standard libs
import sys
from pathlib import Path

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 3rd-party
from alembic.config import main as alembic_main
from sqlalchemy import exc, text

# Local
from app.db_util import ensure_categories_created, ensure_tags_created, get_db_engine
from app.parse_util import parse_data
from app.source import CSV_TYPES


def main(path, csv_type):
    ensure_categories_created()
    ensure_tags_created()
    scraper_cls = CSV_TYPES[csv_type]
    parse_data(path, scraper_cls)


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Path to the file to be parsed")
    parser.add_argument("--csv-type", required=True, choices=CSV_TYPES.keys(), help="Type of CSV")

    args = parser.parse_args()
    engine = get_db_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT * FROM expense")).fetchone()
            conn.execute(text("SELECT * FROM new_id")).fetchone()
    except exc.OperationalError:
        print("Database not initialized. Running alembic migrations...")
        alembic_main(["upgrade", "head"])

    main(args.path, args.csv_type)
