#!/usr/bin/env bash
set -xeuo pipefail

export EXPENSES_DB='sample-expenses.db'
export USE_SAMPLE_CONF=1

HERE=$(dirname "${0}")
PARSE="${HERE}/parse-data.py"

pushd "${HERE}/.."
alembic upgrade head
$PARSE ./sample/axis-cc-statement.csv --csv-type axis-cc
$PARSE ./sample/axis-cc-statement-1.csv --csv-type axis-cc
$PARSE ./sample/axis-statement.csv
$PARSE ./sample/sbi-statement.csv --csv-type sbi
$PARSE ./sample/cash.csv --csv-type cash
if [ -z "${1:-}" ]; then
    streamlit run app/app.py
fi
popd
