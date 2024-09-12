from dataclasses import dataclass

from sqlalchemy.util import classproperty


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

    @classproperty
    def prefix(cls):
        return f"{cls.name}-statement"
