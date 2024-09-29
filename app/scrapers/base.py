import datetime
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.util import classproperty

from app.lib.git_manager import GitManager
from app.model import Expense


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
    columns: dict[str, None | str | list[str]] = {}
    date_format: str = ""
    dtypes: dict[str, str] = {}

    @staticmethod
    def parse_details(expense: Expense) -> Transaction:
        return Transaction()

    @classproperty
    def prefix(cls) -> str:  # noqa: N805
        return f"{cls.name}-statement"

    @classmethod
    def find_files(cls, suffix: str = "csv") -> list[Path]:
        git_manager = GitManager()
        return git_manager.find_files(cls.prefix, suffix=suffix)

    @classmethod
    def fetch_data(
        cls, start_date: datetime.date | None = None, end_date: datetime.date | None = None
    ) -> None:
        raise NotImplementedError
