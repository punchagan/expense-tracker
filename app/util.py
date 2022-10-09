import csv
import datetime
import io
import os
from pathlib import Path

from bs4 import BeautifulSoup


HERE = Path(__file__).parent
ROOT = HERE.parent
DB_NAME = os.getenv("EXPENSES_DB", "expenses.db")


def delta_percent(curr, prev):
    return 100 if prev == 0 else (curr - prev) * 100 / prev


def extract_csv(path, catch_phrase="Transaction Date"):
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
    lines = [line.strip(",") for line in text[start_line:end_line]]
    return io.StringIO("\n".join(lines))


def extract_csv_from_html(htmlfile):
    """Converts html to a CSV."""
    with open(htmlfile) as f:
        soup = BeautifulSoup(f, "html.parser")
    table = soup.findAll("table")[1]
    rows = table.findAll("tr")
    csv_output = io.StringIO()
    csv_rows = [
        [cell.get_text().strip() for cell in row.findAll(["td", "th"])][2:-2]
        for row in rows
    ]
    writer = csv.writer(csv_output)
    writer.writerows(csv_rows)
    csv_output.seek(0)
    return csv_output


def format_month(month):
    return datetime.date(*(month + (1,))).strftime("%b, '%y")


def get_db_url():
    db_path = ROOT.joinpath(DB_NAME)
    return f"sqlite:///{db_path}"
