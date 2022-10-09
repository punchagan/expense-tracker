#!/usr/bin/env bash
set -xeuo pipefail

export EXPENSES_DB='sample-expenses.db'

HERE=$(dirname "${0}")
PARSE="${HERE}/parse-data.py"

pushd "${HERE}/.."
alembic upgrade head
$PARSE ./sample/axis-cc-statement.csv
$PARSE ./sample/axis-cc-statement-1.csv
$PARSE ./sample/axis-statement.csv --catch-phrase 'Tran Date'
$PARSE ./sample/sbi-statement.csv --catch-phrase 'Txn Date'
streamlit run app/app.py
popd
