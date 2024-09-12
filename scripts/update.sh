#!/usr/bin/env bash
set -xeuo pipefail

HERE=$(dirname "$0")

# Make sure DB has the latest structure
alembic upgrade head

# Download data

### Download AC data
LAST_FILE=$(basename "$(find "${DATA_REPO_PATH}"  -name "axis-statement*" | sort | tail -n 1)")
LAST_DATE="${LAST_FILE:18:7}-01"
pytest -k "ac_data" -s "${HERE}/axis-scraper.py" --chrome --headed --uc --start-date "${LAST_DATE:-$(date '+%G-01-01')}" --workers=2 --reruns=5 --reruns-delay=20

### Download CC data
LAST_FILE=$(basename "$(find "${DATA_REPO_PATH}"  -name "axis-cc-statement*" | sort | tail -n 1)")
LAST_DATE="${LAST_FILE:18:7}-01"
pytest -k "cc_data" -s "${HERE}/axis-scraper.py" --chrome --headed --uc --start-date "${LAST_DATE:-$(date '+%G-01-01')}" --workers=2 --reruns=5 --reruns-delay=20

### Download Manual entries data
"${HERE}/gdrive-csv.py"

# Update new data in the database
for each in "${DATA_REPO_PATH}"/*/axis-statement*.csv;
do
    python "${HERE}/parse-data.py" "${each}" --csv-type axis
done
for each in "${DATA_REPO_PATH}"/*/axis-cc-statement*.csv;
do
    python "${HERE}/parse-data.py" "${each}" --csv-type axis-cc
done
python "${HERE}/parse-data.py" "${DATA_REPO_PATH}/cash-${GSHEET_ID}.csv" --csv-type cash

if [ -z "${1:-}" ]; then
    streamlit run app/app.py
fi
