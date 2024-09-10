import csv
import datetime
import io
import os
import sys
import time
from pathlib import Path

from bs4 import BeautifulSoup
import pandas as pd

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.util import extract_csv
from app.lib.git_manager import GitManager

TODAY = datetime.date.today()


def extract_csv_from_html(htmlfile):
    """Converts HTML to a CSV."""
    with open(htmlfile) as f:
        soup = BeautifulSoup(f, "html.parser")
    table = soup.findAll("table")[1]
    rows = table.findAll("tr")
    csv_rows = [
        [cell.get_text().strip() for cell in row.findAll(["td", "th"])][2:-2] for row in rows
    ]
    to_filename = Path(htmlfile).with_suffix(".csv")
    csv_output = io.StringIO()
    writer = csv.writer(csv_output)
    writer.writerows(csv_rows)
    with open(to_filename, "w") as f:
        csv_output.seek(0)
        f.write(extract_csv(csv_output).read())

    print(f"Created {to_filename}")


def remove_currency_prefix(text):
    """Removes the currency prefix from a string."""
    return text.replace("₹", "").strip()


def extract_csv_from_xls(xls_path):
    """Converts XLS(X) to a CSV."""
    data = pd.read_excel(xls_path)
    # Find the header row where first column says "Date"
    header_row_index = int(data[data.iloc[:, 0] == "Date"].index[0])
    headers = data.iloc[header_row_index]
    data = data[int(header_row_index) + 1 : -1]
    data.columns = headers
    data = data.dropna(axis=1, how="all")
    # Add "Debit" and "Credit" columns based on the "Debit/Credit" column
    for key in ("Debit", "Credit"):
        data[key] = data.apply(
            lambda row: (
                remove_currency_prefix(row["Amount (INR)"])
                if key in str(row["Debit/Credit"])
                else None
            ),
            axis=1,
        )

    # Drop the original "Debit/Credit" column and the "Amount (INR)" column
    data = data.drop(columns=["Debit/Credit", "Amount (INR)"])

    data.to_csv(xls_path.with_suffix(".csv"), index=False)


def login(sb):
    sb.open("https://omni.axisbank.co.in/axisretailbanking/")
    username = os.environ["AXIS_USERNAME"]
    password = os.environ["AXIS_PASSWORD"]
    sb.type("input#custid", username)
    sb.type("input#pass", password)
    sb.click("button#APLOGIN")
    time.sleep(3)
    print("Logged in successfully")


def download_account_transactions(sb, start_date, end_date):
    # Select Accounts Card
    sb.click("mat-nav-list#navList1")
    time.sleep(3)

    # Switch to Statements tab
    sb.click("div#mat-tab-label-0-1")
    time.sleep(1)

    # Select Detailed transactions from the dropdown menu
    sb.click_nth_visible_element("div.mat-form-field-infix", 2)
    time.sleep(1)
    sb.click_nth_visible_element("span.mat-option-text", 2)
    time.sleep(1)

    print(f"Downloading monthly account transactions from {start_date} to {end_date}")

    for year in range(start_date.year, end_date.year + 1):
        start_month = 1 if year != start_date.year else start_date.month
        end_month = 12 if year != end_date.year else end_date.month
        for month in range(start_month, end_month + 1):
            download_monthly_account_transactions(sb, year, month)


def download_monthly_account_transactions(sb, year, month):
    # Select From Date
    sb.click("input#state_fromdate")
    ### Open year/month dropdown
    sb.click("div.mat-calendar-header span.mat-button-wrapper")
    UI_FIRST_YEAR = 2001  # Assume years start from 2001
    n_year = year - UI_FIRST_YEAR + 1
    ### Select year, month, date from the calendar dropdowns
    sb.click_nth_visible_element("div.mat-calendar-body-cell-content", n_year)
    sb.click_nth_visible_element("div.mat-calendar-body-cell-content", month)
    sb.click_nth_visible_element("div.mat-calendar-body-cell-content", 1)

    # Select To Date
    sb.click("input#state_todate")
    ### Find num days of month
    first_day = datetime.datetime(year, month, 1)
    if year == TODAY.year and month == TODAY.month:
        n_days = TODAY.day
    else:
        for n_days in range(28, 32):
            last_day = first_day + datetime.timedelta(days=n_days)
            if last_day.month != month:
                break
    ### Open year/month dropdown
    sb.click("div.mat-calendar-header span.mat-button-wrapper")
    UI_FIRST_YEAR = 2001  # Assume years start from 2001
    n_year = year - UI_FIRST_YEAR + 1
    ### Select year, month, date from the calendar dropdowns
    sb.click_nth_visible_element("div.mat-calendar-body-cell-content", n_year)
    sb.click_nth_visible_element("div.mat-calendar-body-cell-content", month)
    sb.click_nth_visible_element(".mat-calendar-body-cell-content", n_days)

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

    git_manager = GitManager()
    git_manager.copy_file_to_repo(Path(path), "axis-ac-statement", year, month)


def download_cc_statement(sb, start_date, end_date):
    print(f"Downloading credit-card transactions from {start_date} to {end_date}")
    # View detailed transaction info
    time.sleep(2)

    # Go to the Dashboard
    sb.click("#navList0")
    time.sleep(2)

    # Click on the Credit Card UI card
    sb.click("div.cards.rCard1")
    time.sleep(2)

    # Switch to the newly opened tab
    sb.switch_to_newest_window()
    time.sleep(5)

    # Close Dialog with popup, if visible
    sb.wait_for_element_absent("div.loading_wrapper")
    sb.click_if_visible(".MuiDialog-container button.MuiIconButton-root")

    # Navigate to Transactions
    sb.wait_for_element_absent("div.loading_wrapper")
    time.sleep(1)
    sb.click("div.coach-step-3")

    # Download XLSX for each month
    for year in range(start_date.year, end_date.year + 1):
        start_month = 1 if year != start_date.year else start_date.month
        end_month = 12 if year != end_date.year else end_date.month
        for month in range(start_month, end_month + 1):
            # Click the Download button
            sb.wait_for_element_absent("div.loading_wrapper")
            time.sleep(1)
            sb.click_nth_visible_element(".TitleCard__body button.MuiButtonBase-root", 2)
            sb.wait_for_element_absent("div.loading_wrapper")
            time.sleep(1)

            # Select the year
            sb.click_nth_visible_element("div.MuiOutlinedInput-input", 1)
            css = f"li[data-value='{year}']"
            if not sb.is_element_present(css):
                print(f"Could not find dropdown for {year}")
                # Close the popup dialog
                sb.click("div.MuiDialog-paper svg.MuiSvgIcon-root")
                continue

            sb.click(css)

            # Click the element whose data-value attribute matches the year
            sb.click_nth_visible_element("div.MuiOutlinedInput-input", 2)
            # Get the data-value by looking at the available options
            data_values = [
                el.get_attribute("data-value") for el in sb.find_elements("li[role=option]")
            ]
            for value in data_values:
                if value.startswith(f"{year}-{month:02}"):
                    break
            else:
                value = None

            if value is None:
                print(f"Could not find dropdown for {year}-{month:02}")
                # Close the popup dialog
                sb.click("div.MuiDialog-paper svg.MuiSvgIcon-root")
                continue

            # Select month
            sb.click(f"li[data-value='{value}']")

            # Select the download format
            sb.click_nth_visible_element("div.MuiOutlinedInput-input", 3)
            sb.click(f"li[data-value='xlsx']")
            sb.click(f".downloadStatement__button-container button")
            time.sleep(5)

            # Save the downloaded file with the correct name
            filename = f"CC_Statement_{TODAY:%Y_%m_%d}.xlsx"
            sb.assert_downloaded_file(filename)

            # Copy the file to the data git repo
            path = Path(sb.get_path_of_downloaded_file(filename))
            git_manager = GitManager()
            new_path = git_manager.copy_file_to_repo(path, "axis-cc-statement", year, month)
            # Convert XLSX to CSV
            extract_csv_from_xls(new_path)
            sb.wait_for_element_absent("div.loading_wrapper")


def test_get_ac_data(sb, start_date, end_date):
    login(sb)
    download_account_transactions(sb, start_date, end_date)


def test_get_cc_data(sb, start_date, end_date):
    login(sb)
    download_cc_statement(sb, start_date, end_date)
