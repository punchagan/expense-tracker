import os
import time


def login(sb):
    sb.open("https://omni.axisbank.co.in/axisretailbanking/")
    username = os.environ["AXIS_USERNAME"]
    password = os.environ["AXIS_PASSWORD"]
    sb.type("input#custid", username)
    sb.type("input#pass", password)
    sb.click("button#APLOGIN")
    time.sleep(3)


def download_account_transactions(sb):
    # Select Detailed Statements
    sb.click("a#ACHMEPG_0")
    time.sleep(3)
    sb.click("div#mat-tab-label-1-1")
    sb.click("div.dynamic-date div.mat-select-value")
    time.sleep(1)
    sb.click_nth_visible_element("span.mat-option-text", 2)
    time.sleep(1)

    # Select Date Range
    sb.click("input#state_fromdate")
    sb.click_nth_visible_element(
        ".mat-calendar-body-cell-content", 24
    )  # FIXME: Date since last crawl
    sb.click("input#state_todate")
    sb.click_nth_visible_element(
        ".mat-calendar-body-cell-content", 29
    )  # FIXME: Today's date
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


def download_cc_statement(sb):
    # View detailed transaction info
    sb.click("#navList0")
    time.sleep(2)
    sb.click("a#CCSSOF_1")
    time.sleep(2)
    sb.switch_to_newest_window()
    time.sleep(2)

    # Navigate to Transactions
    sb.click("div.coach-step-3")
    time.sleep(2)

    # Download Recent Transactions HTML
    sb.click_nth_visible_element(".title-card button.MuiButtonBase-root", 2)
    time.sleep(2)
    sb.click_nth_visible_element(
        "div.download-statement-options__shadow-card-option button.MuiButtonBase-root",
        4,
    )
    sb.assert_downloaded_file(f"CC_Statement_2022_09_28.html")
    time.sleep(2)
    sb.click(".MuiPaper-root svg")

    # Select "Previous" Month
    sb.click(".title-card button.MuiButtonBase-root")
    time.sleep(1)
    sb.click_nth_visible_element("#month-expansion-panel__date-select", 2)
    time.sleep(3)

    # Download Previous Month CSV
    sb.click_nth_visible_element(".title-card button.MuiButtonBase-root", 2)
    time.sleep(3)
    sb.click_nth_visible_element(
        "div.download-statement-options__shadow-card-option button.MuiButtonBase-root",
        3,
    )
    sb.assert_downloaded_file(f"CC_Statement_2022_09_28.csv")
    time.sleep(2)
    sb.click(".MuiPaper-root svg")


def test_get_data(sb):
    login(sb)
    download_account_transactions(sb)
    download_cc_statement(sb)
