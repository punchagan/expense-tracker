# Standard libs
import csv
import io
from pathlib import Path

# 3rd party libs
from bs4 import BeautifulSoup
import pandas as pd


def parse_data(path, catch_phrase):
    if path.endswith(".html"):
        data = extract_csv_from_html(path)
    else:
        data = path

    csv = extract_csv(data, catch_phrase)
    data = pd.read_csv(csv)
    return data


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
        end_line = num

    # Strip leading and trailing commas
    lines = [line.strip(",") for line in text[start_line:end_line]]
    return io.StringIO("\n".join(lines))


def extract_csv_from_html(htmlfile):
    """Converts expenses html file to a csv that can be cleaned."""
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


if __name__ == "__main__":
    import argparse
    from pprint import pprint

    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Path to the file to be parsed")
    parser.add_argument(
        "--catch-phrase",
        default="Transaction Date",
        help="Phrase in file to identify CSV header",
    )

    args = parser.parse_args()
    pprint(parse_data(args.path, args.catch_phrase))
