#!/usr/bin/env python

# Standard libs
import sys
from pathlib import Path

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 3rd-party
from alembic.config import main as alembic_main

from app.parse_util import parse_data
from app.scrapers import AxisStatement, AxisCCStatement, CashStatement
from app.db_util import ensure_categories_created, ensure_tags_created


if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser()
    # Add flag to start streamlit server
    parser.add_argument("--serve", action="store_true", help="Start streamlit server")

    # Ensure DB has the latest structure
    alembic_main(["upgrade", "head"])

    # Download AC data
    AxisStatement.fetch_data()
    AxisCCStatement.fetch_data()
    CashStatement.fetch_data()

    # Ensure tags and categories are created
    ensure_categories_created()
    ensure_tags_created()

    # Parse the data
    for path in AxisStatement.find_files():
        parse_data(path, AxisStatement)

    for path in AxisCCStatement.find_files():
        parse_data(path, AxisCCStatement)

    for path in CashStatement.find_files():
        parse_data(path, CashStatement)

    args = parser.parse_args()
    if args.serve:
        from streamlit.web.cli import main_run

        main_run(["app/app.py"])
