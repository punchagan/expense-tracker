import datetime
import os
import time

TODAY = datetime.date.today()


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
    sb.click_nth_visible_element(".mat-calendar-body-cell-content", end_date.day)
    sb.click("input#state_fromdate")
    for each in range(end_date.month - start_date.month):
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
    sb.assert_downloaded_file(f"{customer}.csv")


def download_cc_statement(sb, start_date):
    end_date = TODAY
    # NOTE: Currently, start_date being in the previous year isn't supported
    # correctly, all the months in the current year get downloaded. This might
    # be a problem if no data is collected after December bill is generated
    # until the next year.
    print(f"Downloading account transactions from {start_date} to {end_date}")
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
    sb.assert_downloaded_file(f"CC_Statement_{TODAY:%Y_%m_%d}.html")
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
        sb.assert_downloaded_file(f"CC_Statement_{name}.html")
        sb.wait_for_element_absent("div.loading_wrapper")
        time.sleep(3)
        sb.click(".MuiPaper-root svg")


def test_get_ac_data(sb, start_date):
    login(sb)
    download_account_transactions(sb, start_date)


def test_get_cc_data(sb, start_date):
    login(sb)
    download_cc_statement(sb, start_date)
