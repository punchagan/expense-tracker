#!/usr/bin/env bash
set -xeuo pipefail

HERE=$(dirname "$0")

pushd "${HERE}/.."
LAST_DATE=$(sqlite3 "${EXPENSES_DB}" 'SELECT MAX(date) FROM expense;' | cut -d " " -f 1) || true
popd

TODAY=$(date +%Y_%m_%d)

# Make sure DB has the latest structure
alembic upgrade head

# Download data
pytest -s "${HERE}/axis-scraper.py" --browser=firefox --start-date "${LAST_DATE:-2022-01-01}" --workers=2 --reruns=5 --reruns-delay=20 --archive-downloads
"${HERE}/gdrive-csv.py"

# Update new data in the database
python "${HERE}/parse-data.py" "${HERE}/../downloaded_files/${AXIS_CUSTOMID}.csv" --csv-type axis
for each in $(ls "${HERE}/../downloaded_files/CC_Statement_${TODAY}"*".csv");
do
    python "${HERE}/parse-data.py" "${each}" --csv-type axis-cc
done
python "${HERE}/parse-data.py" "${HERE}/../downloaded_files/${GSHEET_ID}.csv" --csv-type cash

if [ -z "${1:-}" ]; then
    streamlit run app/app.py
fi
