import csv
import datetime
import io
import os
import sys
import time
from pathlib import Path

from bs4 import BeautifulSoup

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.util import extract_csv

TODAY = datetime.date.today()


def extract_csv_from_html(htmlfile):
    """Converts HTML to a CSV."""
    with open(htmlfile) as f:
        soup = BeautifulSoup(f, "html.parser")
    table = soup.findAll("table")[1]
    rows = table.findAll("tr")
    csv_rows = [
        [cell.get_text().strip() for cell in row.findAll(["td", "th"])][2:-2]
        for row in rows
    ]
    to_filename = Path(htmlfile).with_suffix(".csv")
    csv_output = io.StringIO()
    writer = csv.writer(csv_output)
    writer.writerows(csv_rows)
    with open(to_filename, "w") as f:
        csv_output.seek(0)
        f.write(extract_csv(csv_output).read())

    print(f"Created {to_filename}")


def login(sb):
    sb.open("https://omni.axisbank.co.in/axisretailbanking/")
    username = os.environ["AXIS_USERNAME"]
    password = os.environ["AXIS_PASSWORD"]
    sb.type("input#custid", username)
    sb.type("input#pass", password)
    sb.click("button#APLOGIN")
    time.sleep(3)
    print("Logged in successfully")


def download_account_transactions(sb, start_date):
    end_date = TODAY
    if (end_date - start_date).days > 360:
        end_date = start_date + datetime.timedelta(days=360)
    print(f"Downloading account transactions from {start_date} to {end_date}")

    # Select Detailed Statements
    sb.click("a#ACHMEPG_0")
    time.sleep(3)
    sb.click("div#mat-tab-label-1-1")
    sb.click("div.dynamic-date div.mat-select-value")
    time.sleep(1)
    sb.click_nth_visible_element("span.mat-option-text", 2)
    time.sleep(1)

    # Select Date Range
    sb.click("input#state_todate")
    num_months = (TODAY.year - end_date.year) * 12 + (TODAY.month - end_date.month)
    for _ in range(num_months):
        sb.click("button.mat-calendar-previous-button")
    sb.click_nth_visible_element(".mat-calendar-body-cell-content", end_date.day)
    sb.click("input#state_fromdate")
    num_months = (TODAY.year - start_date.year) * 12 + (TODAY.month - start_date.month)
    for _ in range(num_months):
        sb.click("button.mat-calendar-previous-button")
    sb.click_nth_visible_element(".mat-calendar-body-cell-content", start_date.day)
    time.sleep(1)
    sb.click("a#go")

    # Choose CSV
    sb.click("#topDownload")
    time.sleep(1)
    sb.click_nth_visible_element("span.mat-option-text", 4)

    # Download
    sb.click("#StatementInputFilter0")
    customer = os.environ["AXIS_CUSTOMID"]
    filename = f"{customer}.csv"
    sb.assert_downloaded_file(filename)
    path = sb.get_path_of_downloaded_file(filename)
    text = extract_csv(path, catch_phrase="Tran Date")
    with open(path, "w") as f:
        f.write(text.read())


def download_cc_statement(sb, start_date):
    end_date = TODAY
    # NOTE: Currently, start_date being in the previous year isn't supported
    # correctly, all the months in the current year get downloaded. This might
    # be a problem if no data is collected after December bill is generated
    # until the next year.
    print(f"Downloading credit-card transactions from {start_date} to {end_date}")
    # View detailed transaction info
    time.sleep(2)
    sb.click("#navList0")
    time.sleep(2)
    sb.click("a#CCSSOF_1")
    time.sleep(2)
    sb.switch_to_newest_window()
    time.sleep(5)

    # Navigate to Transactions
    sb.wait_for_element_absent("div.loading_wrapper")
    time.sleep(1)
    sb.click("div.coach-step-3")

    # Download Recent Transactions HTML
    sb.wait_for_element_absent("div.loading_wrapper")
    time.sleep(1)
    sb.click_nth_visible_element(".title-card button.MuiButtonBase-root", 2)
    sb.wait_for_element_absent("div.loading_wrapper")
    time.sleep(1)
    sb.click_nth_visible_element(
        "div.download-statement-options__shadow-card-option button.MuiButtonBase-root",
        4,
    )
    sb.wait_for_element_absent("div.loading_wrapper")
    time.sleep(1)
    filename = f"CC_Statement_{TODAY:%Y_%m_%d}.html"
    sb.assert_downloaded_file(filename)
    path = sb.get_path_of_downloaded_file(filename)
    extract_csv_from_html(path)
    sb.wait_for_element_absent("div.loading_wrapper")
    time.sleep(1)
    sb.click(".MuiPaper-root svg")
    sb.wait_for_element_absent("div.loading_wrapper")
    time.sleep(1)

    repeat_months = (
        end_date.month - (start_date.month - 1)
        if end_date.year == start_date.year
        else end_date.month
    )

    sb.click(".title-card button.MuiButtonBase-root")
    sb.wait_for_element_absent("div.loading_wrapper")
    time.sleep(1)
    months = len(sb.find_visible_elements("#month-expansion-panel__date-select"))
    sb.click(".MuiPaper-root svg")

    for index in range(0, min(repeat_months, months - 1)):
        # Select "Previous" Month
        sb.click(".title-card button.MuiButtonBase-root")
        sb.wait_for_element_absent("div.loading_wrapper")
        time.sleep(3)
        sb.click_nth_visible_element("#month-expansion-panel__date-select", 2 + index)
        sb.wait_for_element_absent("div.loading_wrapper")
        time.sleep(3)

        # Download Previous Month HTML (CSVs don't work for all months)
        sb.click_nth_visible_element(".title-card button.MuiButtonBase-root", 2)
        sb.wait_for_element_absent("div.loading_wrapper")
        time.sleep(3)
        sb.click_nth_visible_element(
            "div.download-statement-options__shadow-card-option button.MuiButtonBase-root",
            4,
        )
        sb.wait_for_element_absent("div.loading_wrapper")
        time.sleep(3)
        name = f"{TODAY:%Y_%m_%d}({index + 1})"
        filename = f"CC_Statement_{name}.html"
        sb.assert_downloaded_file(filename)
        path = sb.get_path_of_downloaded_file(filename)
        extract_csv_from_html(path)
        sb.wait_for_element_absent("div.loading_wrapper")
        time.sleep(3)
        sb.click(".MuiPaper-root svg")


def test_get_ac_data(sb, start_date):
    login(sb)
    download_account_transactions(sb, start_date)


def test_get_cc_data(sb, start_date):
    login(sb)
    download_cc_statement(sb, start_date)
