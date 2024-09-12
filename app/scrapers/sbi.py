#!/usr/bin/env python3

import os
import requests

from app.lib.git_manager import GitManager
from app.source import Source, Transaction


class SBIStatement(Source):
    name = "sbi"
    columns = {
        "date": "Txn Date",
        "details": "Description",
        "credit": "Credit",
        "debit": "Debit",
        "amount": None,
    }
    date_format = "%d %b %Y"
    dtypes = {"Debit": "float64", "Credit": "float64"}

    @classmethod
    def fetch_data(cls):
        raise NotImplementedError(
            "Fetching data for SBI is not implemented yet. "
            "Manually download the data (TSV) and "
            "use the scripts/sbi-read-csv.py."
        )

    @staticmethod
    def parse_details(expense, country, cities):
        raise NotImplementedError("Parsing details for SBI is not implemented yet.")
