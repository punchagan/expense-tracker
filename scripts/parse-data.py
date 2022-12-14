#!/usr/bin/env python

# Standard libs
import sys
from pathlib import Path

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 3rd-party
from alembic.config import main as alembic_main

# Local
from app.db_util import ensure_categories_created, ensure_tags_created, get_db_engine
from app.parse_util import parse_data
from app.source import CSV_TYPES


def main(path, csv_type):
    ensure_categories_created()
    ensure_tags_created()
    parse_data(path, csv_type)


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Path to the file to be parsed")
    parser.add_argument(
        "--csv-type", required=True, choices=CSV_TYPES.keys(), help="Type of CSV"
    )

    args = parser.parse_args()
    engine = get_db_engine()
    try:
        engine.execute("SELECT * FROM expense").fetchone()
        engine.execute("SELECT * FROM new_id").fetchone()
    except exc.OperationalError:
        alembic_main(["upgrade", "head"])

    main(args.path, args.csv_type)
