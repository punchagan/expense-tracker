import csv
import datetime
import io
import os
import time
from pathlib import Path
import re

from bs4 import BeautifulSoup
import pandas as pd
from seleniumbase import SB

from app.util import extract_csv
from app.lib.git_manager import GitManager
from app.source import Source, Transaction

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


def download_account_transactions(sb, name, start_date, end_date):
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
            download_monthly_account_transactions(sb, name, year, month)


def download_monthly_account_transactions(sb, name, year, month):
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
    git_manager.copy_file_to_repo(Path(path), f"{name}-statement", year, month)


def download_cc_statement(sb, name, start_date, end_date):
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
            sb.click("li[data-value='xlsx']")
            sb.click(".downloadStatement__button-container button")
            time.sleep(5)

            # Save the downloaded file with the correct name
            filename = f"CC_Statement_{TODAY:%Y_%m_%d}.xlsx"
            sb.assert_downloaded_file(filename)

            # Copy the file to the data git repo
            path = Path(sb.get_path_of_downloaded_file(filename))
            git_manager = GitManager()
            new_path = git_manager.copy_file_to_repo(path, f"{name}-statement", year, month)
            # Convert XLSX to CSV
            extract_csv_from_xls(new_path)
            sb.wait_for_element_absent("div.loading_wrapper")


class AxisStatement(Source):
    name = "axis"
    columns = {
        "date": "Tran Date",
        "details": "PARTICULARS",
        "credit": "CR",
        "debit": "DR",
        "amount": None,
    }
    date_format = "%d-%m-%Y"
    dtypes = {"DR": "float64", "CR": "float64"}

    @classmethod
    def fetch_data(cls, start_date=None, end_date=None):
        if start_date is None:
            git_manager = GitManager()
            latest_file = git_manager.find_latest_file(f"{cls.name}-statement")
            year, month = map(int, latest_file.stem.rsplit("-", 2)[-2:])
            start_date = datetime.date(year, month, 1)

        if end_date is None:
            end_date = TODAY

        with SB(uc=True, browser="chrome", headed=True) as sb:
            login(sb)
            download_account_transactions(sb, cls.name, start_date, end_date)

    @staticmethod
    def parse_details(expense, country, cities):
        details = expense.details.replace("M/s", "M.s")
        axis_id = os.getenv("AXIS_CUSTOMID", "")
        if details.startswith("UPIRECONP2PM/"):
            _, transaction_id, _ = [each.strip() for each in details.split("/", 2)]
            transaction = Transaction(
                transaction_type="UPI",
                counterparty_type="Merchant",
                remarks=details,
            )
        elif details.startswith("TIPS/"):
            transaction_id = details.split("/")[3] if details.count("/") == 5 else ""
            transaction = Transaction(
                transaction_id=transaction_id,
                transaction_type="SCG",
                counterparty_type="Merchant",
                remarks=details.rsplit("/", 1)[0],
            )
        elif details.startswith("CTF "):
            extra = details.split()[-1]
            to_name = re.search("[A-Z]+", extra)
            to_name = to_name.group() if to_name else ""
            transaction_id = re.search("[0-9]+", extra)
            transaction_id = transaction_id.group() if transaction_id else ""
            transaction = Transaction(
                transaction_type="UPI",
                transaction_id=transaction_id,
                counterparty_name=to_name.title(),
                counterparty_type="Merchant",
                remarks=details,
            )
        elif details.startswith("UPI/CRADJ/"):
            _, _, transaction_id, _ = [each.strip() for each in details.split("/", 3)]
            transaction = Transaction(
                transaction_type="UPI",
                transaction_id=transaction_id,
                counterparty_type="Merchant",
                remarks=details,
            )
        elif details.startswith("UPI/"):
            transaction_type, to_type, transaction_id, to_name, extra = [
                each.strip() for each in details.split("/", 4)
            ]
            if "/" in extra:
                to_bank, remarks = extra.split("/", 1)
            else:
                to_bank = ""
                remarks = extra

            # The transaction format was changed later to interchange bank name
            # and remarks. Remarks are truncated to 6 characters, in the new
            # format.
            if len(to_bank) <= 6:
                to_bank, remarks = remarks, to_bank
            transaction = Transaction(
                transaction_id=transaction_id,
                transaction_type=transaction_type,
                counterparty_name=to_name.title().strip(),
                counterparty_type=to_type.strip(),
                counterparty_bank=to_bank.strip(),
                remarks=remarks.strip("/").strip(),
            )

        elif details.startswith("IMPS/"):
            transaction_type, to_type, transaction_id, to_name, extra = [
                each.strip() for each in details.split("/", 4)
            ]
            # FIXME: if to_name is same as axis_id, then it is a credit
            if extra.count("/") == 0:
                to_bank = ""
                remarks = extra
            elif extra.count("/") == 1:
                to_bank, remarks = [each.strip() for each in extra.split("/", 1)]
                if to_bank.startswith(("X", "0")):
                    to_bank, remarks = remarks, to_bank
            else:
                extra_remarks = extra.split("/", 2)
                to_bank = (
                    extra_remarks[1]
                    if extra_remarks[0].startswith(("X", "0"))
                    else extra_remarks[0]
                )
                remarks = "/".join(
                    [extra_remarks[0], extra_remarks[2]]
                    if extra_remarks[0].startswith(("X", "0"))
                    else extra_remarks[1:]
                )
            transaction = Transaction(
                transaction_id=transaction_id,
                transaction_type=transaction_type,
                counterparty_name=to_name.title().strip(),
                counterparty_type=to_type.strip(),
                counterparty_bank=to_bank.strip(),
                remarks=remarks.strip("/").strip(),
            )

        elif details.startswith(("NEFT/")):
            transaction_type, to_type, transaction_id, to_name, extra = [
                each.strip() for each in details.split("/", 4)
            ]
            if to_type not in {"P2M", "P2A", "MB"}:
                transaction_id, to_name, to_type, to_bank = to_type, transaction_id, "MB", to_name
                remarks = extra.rsplit("/", 1)[-1]
            else:
                extra = extra.replace("/ATTN/", "ATTN")
                to_bank, remarks = extra.split("/", 1)
            transaction = Transaction(
                transaction_id=transaction_id,
                transaction_type=transaction_type,
                counterparty_name=to_name.title().strip(),
                counterparty_type=to_type.strip(),
                counterparty_bank=to_bank.strip(),
                remarks=remarks.strip("/").strip(),
            )
        elif details.startswith("NBSM/"):
            transaction_type, transaction_id, to_name, remarks = [
                each.strip() for each in details.split("/", 3)
            ]
            transaction = Transaction(
                transaction_id=transaction_id,
                transaction_type=transaction_type,
                counterparty_name=to_name.title().strip(),
                remarks=remarks.strip("/").strip(),
            )
        elif details.startswith("ECOM PUR/"):
            transaction_type, to_name, _ = [each.strip() for each in details.split("/", 2)]
            transaction = Transaction(
                transaction_type="ECOM",
                counterparty_name=to_name.title(),
                counterparty_type="Merchant",
            )
        elif details.startswith("POS/"):
            transaction_type, to_name, transaction_id, _ = [
                each.strip() for each in details.split("/", 3)
            ]
            transaction = Transaction(
                transaction_type="POS",
                counterparty_name=to_name.title(),
                counterparty_type="Merchant",
            )
        elif details.startswith("ATM-CASH"):
            _, remarks = [each.strip() for each in details.split("/", 1)]
            transaction = Transaction(
                transaction_type="ATM",
                counterparty_name="ATM",
                remarks=remarks,
            )
        elif details.startswith("BRN-CLG-CHQ"):
            _, counterparty_name = [each.strip() for each in details.split("PAID TO", 1)]
            transaction = Transaction(transaction_type="CHQ", counterparty_name=counterparty_name)
        elif (
            re.search(
                "(SMS Alerts|Monthly|Consolidated|GST|Dr Card|Excess).*(Chrg|Charge|Service Fee)",
                details,
                flags=re.IGNORECASE,
            )
            is not None
        ):
            transaction = Transaction(
                transaction_type="AC",
                counterparty_name="Axis Bank",
                counterparty_type="Merchant",
                remarks=details,
            )
        elif details.startswith("CreditCard Payment"):
            transaction = Transaction(
                transaction_type="AC",
                transaction_id=details.rsplit("#", 1)[-1],
                counterparty_name="CreditCard Payment",
                counterparty_type="Merchant",
                ignore=True,
            )
        elif axis_id and f"{axis_id}:" in details:
            transaction = Transaction(
                transaction_type="AC",
                counterparty_name="Axis Bank",
                counterparty_type="Merchant",
                remarks=details[len(axis_id) + 1 :],
            )
        elif details.startswith("BRN-PYMT-CARD"):
            transaction = Transaction(
                transaction_type="AC",
                counterparty_name="Axis Bank",
                counterparty_type="Merchant",
                remarks=details,
                ignore=True,
            )
        else:
            # FIXME: Leave this in for debugging, with a commandline arg
            # import pdb
            # pdb.set_trace()
            raise RuntimeError(f"Unknown Transaction Type: {details}")

        return transaction


class AxisCCStatement(Source):
    name = "axis-cc"
    columns = {
        "date": "Date",
        "details": "Transaction Details",
        "credit": "Credit",
        "debit": "Debit",
        "amount": None,
    }
    date_format = "%d %b '%y"
    dtypes = {"Debit": "float64", "Credit": "float64"}

    @classmethod
    def fetch_data(cls, start_date=None, end_date=None):
        if start_date is None:
            git_manager = GitManager()
            latest_file = git_manager.find_latest_file(f"{cls.name}-statement")
            year, month = map(int, latest_file.stem.rsplit("-", 2)[-2:])
            start_date = datetime.date(year, month, 1)

        if end_date is None:
            end_date = TODAY

        with SB(uc=True, browser="chrome", headed=True) as sb:
            login(sb)
            download_cc_statement(sb, cls.name, start_date, end_date)

    @staticmethod
    def parse_details(expense, country, cities):
        details = expense.details
        merchant = details.split(",", 1)[0]
        ignore = details.startswith("MB PAYMENT")
        return Transaction(
            transaction_type="CC",
            counterparty_name=merchant.title(),
            counterparty_type="Merchant",
            ignore=ignore,
        )
