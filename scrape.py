import os
import time


def test_get_data(sb):
    sb.open("https://omni.axisbank.co.in/axisretailbanking/")
    username = os.environ["AXIS_USERNAME"]
    password = os.environ["AXIS_PASSWORD"]
    customer = os.environ["AXIS_CUSTOMID"]

    # Login
    sb.type("input#custid", username)
    sb.type("input#pass", password)
    sb.click("button#APLOGIN")
    time.sleep(3)

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
    sb.assert_downloaded_file(f"{customer}.csv")
