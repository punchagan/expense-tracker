import os
import requests

from app.lib.git_manager import GitManager
from app.source import Source, Transaction


class CashStatement(Source):
    name = "cash"
    columns = {
        "date": "Timestamp",
        "details": ["Details", "Category"],
        "credit": None,
        "debit": None,
        "amount": "Amount",
    }
    date_format = "%d/%m/%Y %H:%M:%S"
    dtypes = {"Amount": "float64"}

    @classmethod
    def fetch_data(cls):
        git_manager = GitManager()
        sheet_id = os.environ["GSHEET_ID"]
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        response = requests.get(url)
        csv_path = git_manager.repo_path.joinpath(f"{cls.name}-statement-{sheet_id}.csv")
        with open(csv_path, "w") as f:
            f.write(response.text)

    @staticmethod
    def parse_details(expense, country, cities):
        details = expense.details
        remarks, category_name = [each.strip() for each in details.split("/")]
        return Transaction(
            transaction_type="Cash",
            remarks=remarks,
            category_name=category_name,
        )
