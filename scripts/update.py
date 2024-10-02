#!/usr/bin/env python

# Standard libs
import sys
from pathlib import Path

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 3rd-party
from alembic.config import main as alembic_main

# Local
from app.db_util import ensure_categories_created, ensure_tags_created
from app.parse_util import parse_data
from app.scrapers import ALL_SCRAPERS
from app.util import CONFIG

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true", help="Start streamlit server")
    parser.add_argument(
        "--scrapers",
        nargs="*",
        choices=ALL_SCRAPERS.keys(),
        help="Specify one or more scrapers to use",
    )
    parser.add_argument("--no-fetch", action="store_true", help="Skip fetching data")
    parser.add_argument("--no-parse", action="store_true", help="Skip parsing data")
    args = parser.parse_args()

    # Ensure DB has the latest structure
    alembic_main(["upgrade", "head"])

    # Ensure tags and categories are created
    ensure_categories_created()
    ensure_tags_created()

    scrapers_to_use = sorted(set(args.scrapers)) if args.scrapers else CONFIG.get("scrapers", [])

    if not scrapers_to_use:
        parser.error("Please define scrapers in conf.py or use --scrapers to specify them.")

    # Fetch data if not skipped
    if not args.no_fetch:
        for scraper_name in scrapers_to_use:
            scraper = ALL_SCRAPERS[scraper_name]
            scraper.fetch_data()

    # Parse data if not skipped
    if not args.no_parse:
        for scraper_name in scrapers_to_use:
            scraper = ALL_SCRAPERS[scraper_name]
            for path in scraper.find_files():
                parse_data(path, scraper)

    if args.serve:
        from streamlit.web.cli import main_run

        main_run(["app/app.py"])
