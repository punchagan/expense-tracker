#!/usr/bin/env bash
set -xeuo pipefail

ROOT="$(dirname "${0}")/.."

curl https://raw.githubusercontent.com/nshntarora/Indian-Cities-JSON/master/cities.json | jq -r '[.[].name] + ["Bangalore"] | sort' > "${ROOT}/data/indian-cities.json"

# Country list is JSON-ified version of https://www.iban.com/country-codes
