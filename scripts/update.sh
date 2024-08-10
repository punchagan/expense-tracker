#!/usr/bin/env bash
set -xeuo pipefail

HERE=$(dirname "$0")

pushd "${HERE}/.."
LAST_DATE=$(sqlite3 "${EXPENSES_DB}" 'SELECT MAX(date) FROM expense;' | cut -d " " -f 1) || true
echo "Last date: ${LAST_DATE}"
popd

TODAY=$(date +%Y_%m_%d)

# Make sure DB has the latest structure
alembic upgrade head

# Download data
pytest -s "${HERE}/axis-scraper.py" --browser=chrome --uc --start-date "${LAST_DATE:-2022-01-01}" --workers=2 --reruns=5 --reruns-delay=20 --archive-downloads
"${HERE}/gdrive-csv.py"

# Update new data in the database
for each in "${DATA_REPO_PATH}"/*/axis-ac-statement*.csv;
do
    python "${HERE}/parse-data.py" "${each}" --csv-type axis
done
for each in "${DATA_REPO_PATH}"/*/axis-cc-statement*.csv;
do
    python "${HERE}/parse-data.py" "${each}" --csv-type axis-cc
done
python "${HERE}/parse-data.py" "${DATA_REPO_PATH}/manual-entries-${GSHEET_ID}.csv" --csv-type cash

if [ -z "${1:-}" ]; then
    streamlit run app/app.py
fi
