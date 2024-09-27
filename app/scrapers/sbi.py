import datetime
from typing import NoReturn

from app.model import Expense

from .base import Source


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
    def fetch_data(
        cls, start_date: datetime.date | None = None, end_date: datetime.date | None = None
    ) -> NoReturn:
        raise NotImplementedError(
            "Fetching data for SBI is not implemented yet. "
            "Manually download the data (TSV) and "
            "use the scripts/sbi-read-csv.py."
        )

    @staticmethod
    def parse_details(expense: Expense) -> NoReturn:
        raise NotImplementedError("Parsing details for SBI is not implemented yet.")
