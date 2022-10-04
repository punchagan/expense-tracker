#!/usr/bin/env bash
set -xeuo pipefail

HERE=$(dirname "$0")
LAST_DATE=$(sqlite3 "${HERE}/../expenses.db" 'SELECT MAX(date) FROM expenses;' | cut -d " " -f 1) || true
TODAY=$(date +%Y_%m_%d)

# Download data
pytest -sv "${HERE}/axis-scraper.py" --browser=firefox --start-date "${LAST_DATE:-2022-01-01}" --workers=2 --reruns=3 --reruns-delay=20

# Update new data in the database
python "${HERE}/parse-data.py" "${HERE}/../downloaded_files/${AXIS_CUSTOMID}.csv" --catch-phrase 'Tran Date'
python "${HERE}/parse-data.py" "${HERE}/../downloaded_files/CC_Statement_${TODAY}.csv"
python "${HERE}/parse-data.py" "${HERE}/../downloaded_files/CC_Statement_${TODAY}.html"
