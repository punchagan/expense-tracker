from dataclasses import dataclass


@dataclass
class Transaction:
    transaction_id: str = ""
    transaction_type: str = ""
    counterparty_name: str = ""
    counterparty_type: str = ""
    counterparty_bank: str = ""
    remarks: str = ""
    category_name: str = ""
    ignore: bool = False


class Source:
    name = "base"
    columns = {}
    date_format = None

    @staticmethod
    def parse_details(expense, country, cities):
        return Transaction()


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


CSV_TYPES = {kls.name: kls for kls in Source.__subclasses__()}
