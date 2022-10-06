#!/usr/bin/env bash
set -xeuo pipefail

export EXPENSES_DB='sample-expenses.db'

HERE=$(dirname "${0}")
PARSE="${HERE}/parse-data.py"

pushd "${HERE}/.."
$PARSE ./sample/axis-cc-statement.csv
$PARSE ./sample/axis-cc-statement.html
$PARSE ./sample/axis-statement.csv --catch-phrase 'Tran Date'
streamlit run app.py
popd
