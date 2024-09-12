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


class Cash(Source):
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

    @staticmethod
    def parse_details(expense, country, cities):
        details = expense.details
        remarks, category_name = [each.strip() for each in details.split("/")]
        return Transaction(
            transaction_type="Cash",
            remarks=remarks,
            category_name=category_name,
        )


CSV_TYPES = {kls.name: kls for kls in Source.__subclasses__()}
