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
    def fetch_data(cls):
        raise NotImplementedError(
            "Fetching data for SBI is not implemented yet. "
            "Manually download the data (TSV) and "
            "use the scripts/sbi-read-csv.py."
        )

    @staticmethod
    def parse_details(expense):
        raise NotImplementedError("Parsing details for SBI is not implemented yet.")
