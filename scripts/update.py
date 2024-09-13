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

    scrapers = [AxisStatement, AxisCCStatement, CashStatement]

    # Download AC data
    for scraper in scrapers:
        scraper.fetch_data()

    # Ensure tags and categories are created
    ensure_categories_created()
    ensure_tags_created()

    # Parse the data
    for scraper in scrapers:
        for path in scraper.find_files():
            parse_data(path, scraper)

    args = parser.parse_args()
    if args.serve:
        from streamlit.web.cli import main_run

        main_run(["app/app.py"])
