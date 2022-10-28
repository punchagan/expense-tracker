import calendar
import datetime
import io
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).parent
ROOT = HERE.parent
DB_NAME = os.getenv("EXPENSES_DB", "expenses.db")
USE_SAMPLE_CONF = "USE_SAMPLE_CONF" in os.environ

if USE_SAMPLE_CONF:
    sys.path.insert(0, str(ROOT.joinpath("sample")))


def daterange_from_year_month(year, month):
    if year > 0 and 0 < month < 13:
        start_date = datetime.datetime(year, month, 1)
        _, num_days = calendar.monthrange(year, month)
        end_date = start_date + datetime.timedelta(days=num_days)
    elif year > 0:
        start_date = datetime.datetime(year, 1, 1)
        end_date = datetime.datetime(year + 1, 1, 1)
    else:
        start_date = datetime.datetime(1900, 1, 1)
        end_date = datetime.datetime(2100, 1, 1)

    return start_date, end_date


def delta_percent(curr, prev):
    if prev == 0:
        sign = "-" if curr <= 0 else "+"
        return f"{sign} unknown"
    delta = (curr - prev) * 100 / prev
    return f"{delta:.2f} %"


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
    lines = [line.strip().strip(",") for line in text[start_line:end_line]]
    return io.StringIO("\n".join(lines))


def format_month(month):
    year, month = month
    if year > 0 and month < 13:
        return datetime.date(year, month, 1).strftime(r"⠀⠀%b, '%y")
    if year > 0:
        return datetime.date(year, 1, 1).strftime("⠀%Y")
    return "All"


def get_db_url():
    db_path = ROOT.joinpath(DB_NAME)
    return f"sqlite:///{db_path}"


def get_country_data(country):
    if country == "India":
        cities = ROOT.joinpath("data", "indian-cities.json")
        countries = ROOT.joinpath("data", "country-codes.json")
        with open(countries) as f:
            countries_data = json.load(f)
            country = [c for c in countries_data if c["name"] == country][0]

        with open(cities) as f:
            cities_data = json.load(f)

        return country, cities_data
    else:
        raise NotImplementedError


def previous_month(start_date):
    end = start_date
    prev = end - datetime.timedelta(days=1)
    start = datetime.date(prev.year, prev.month, 1)
    return start, end


def lookup_counterparty_names(engine):
    names = engine.execute(
        "SELECT source, counterparty_name_p, counterparty_name FROM expense"
    ).fetchall()
    lookup = {
        (source, parsed_name): name
        for source, parsed_name, name in names
        if parsed_name and parsed_name != name
    }
    return lookup
