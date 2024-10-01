import calendar
import datetime
import io
import os
import sys
from pathlib import Path

import pytz

HERE = Path(__file__).parent
ROOT = HERE.parent
NUM_MONTHS = 12
DATA_REPO_PATH = Path(os.getenv("DATA_REPO_PATH", Path.cwd() / "data.git"))

sys.path.insert(0, str(DATA_REPO_PATH))

try:
    from conf import TIMEZONE
except ImportError:
    TIMEZONE = "Asia/Kolkata"

TZINFO = pytz.timezone(TIMEZONE)


def today() -> datetime.date:
    return datetime.datetime.now(tz=TZINFO).date()


def daterange_from_year_month(year: int, month: int) -> tuple[datetime.date, datetime.date, int]:
    if year > 0 and 0 < month <= NUM_MONTHS:
        start_date = datetime.date(year, month, 1)
        _, num_days = calendar.monthrange(year, month)
        end_date = start_date + datetime.timedelta(days=num_days)
    elif year > 0:
        start_date = datetime.date(year, 1, 1)
        end_date = datetime.date(year + 1, 1, 1)
        num_days = 31
    else:
        start_date = datetime.date(1900, 1, 1)
        end_date = datetime.date(2100, 1, 1)
        num_days = 31

    return start_date, end_date, num_days


def delta_percent(curr: float, prev: float) -> str:
    if prev == 0:
        sign = "-" if curr <= 0 else "+"
        return f"{sign} unknown"
    delta = (curr - prev) * 100 / abs(prev)
    return f"{delta:.2f} %"


def extract_csv(path: str | io.StringIO, catch_phrase: str = "Transaction Date") -> io.StringIO:
    """Extact CSV part of a file, based on a catch phrase in the header."""

    if isinstance(path, io.StringIO):
        text = path.read().strip().splitlines()

    else:
        with open(path) as f:
            text = f.read().strip().splitlines()

    if not text:
        return io.StringIO("")

    start_line = None
    end_line = None

    for num, line in enumerate(text):
        # Set beginning of CSV if catch_phrase is found in a line
        if catch_phrase in line:
            start_line = num
        # Set end of CSV as the first empty line after the header
        elif start_line is not None and not line.strip():
            end_line = num
            break
        else:
            continue
    else:
        # If there's no empty line, continue until the end
        end_line = num + 1

    # Strip leading and trailing commas
    lines = [line.strip().strip(",") for line in text[start_line:end_line]]
    return io.StringIO("\n".join(lines))


def format_month(year_month: tuple[int, int]) -> str:
    year, month = year_month
    if year > 0 and month <= NUM_MONTHS:
        return datetime.date(year, month, 1).strftime(r"⠀⠀%b, '%y")
    if year > 0:
        return datetime.date(year, 1, 1).strftime("⠀%Y")
    return "All"


def previous_month(end: datetime.date) -> tuple[datetime.date, datetime.date]:
    prev = end - datetime.timedelta(days=1)
    start = datetime.date(prev.year, prev.month, 1)
    return start, end
