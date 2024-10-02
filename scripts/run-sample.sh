#!/usr/bin/env bash
set -xeuo pipefail

export EXPENSES_DB='sample-expenses.db'
export DATA_REPO_PATH="sample/git"

HERE=$(dirname "${0}")

# Make a temporary git repository from the sample data
git init "${DATA_REPO_PATH}"
cp sample/*.* "${DATA_REPO_PATH}/"

pushd "${HERE}/.."
alembic upgrade head

./scripts/update.py --no-fetch
if [ -z "${1:-}" ]; then
    streamlit run app/app.py
fi
popd

