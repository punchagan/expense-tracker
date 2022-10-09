import datetime
import os
from pathlib import Path


HERE = Path(__file__).parent
ROOT = HERE.parent
DB_NAME = os.getenv("EXPENSES_DB", "expenses.db")


def delta_percent(curr, prev):
    return 100 if prev == 0 else (curr - prev) * 100 / prev


def format_month(month):
    return datetime.date(*(month + (1,))).strftime("%b, '%y")


def get_db_url():
    db_path = ROOT.joinpath(DB_NAME)
    return f"sqlite:///{db_path}"
