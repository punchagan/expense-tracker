#!/usr/bin/env bash
set -xeuo pipefail

export EXPENSES_DB='sample-expenses.db'
export USE_SAMPLE_CONF=1

HERE=$(dirname "${0}")

pushd "${HERE}/.."
alembic upgrade head

# Make a temporary git repository from the sample data
export DATA_REPO_PATH="sample/git"
git init "${DATA_REPO_PATH}"
cp sample/*.* "${DATA_REPO_PATH}/"

./scripts/update.py --no-fetch
if [ -z "${1:-}" ]; then
    streamlit run app/app.py
fi
popd

