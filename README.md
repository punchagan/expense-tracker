# Expense Tracker

Expense tracker aims to build a simple UI to track monthly expenses.

It is a collection of scripts to scrape and parse transaction data from
bank/credit-card statements and dump them into a local SQLite DB.  There's a
simple UI that interacts with this local DB that lets the user explore and
analyse their spending patterns.

## Why build one yourself?

We use a lot of Internet Banking these days, but I still don't feel comfortable
sharing information about all my expenses with a 3rd-party.  So, I built a tool
that runs locally on my computer and can only be accessed locally.

## How do I use it?

The repository currently contains:

- Data Scrapers
  - Axis Bank

- Data Parsers
  - SBI (downloaded tsv/xls)
  - Axis Bank (scraped/downloaded data)
  - Manual entries (Cash)

But, other scrapers/parsers could be easily written.

### Parsing transactional SMS messages

Another commonly used approach for tools like this is to parse SMS's sent by
banks to get information about expenses. I considered this approach initially,
but it turned out that that SMS's sent by my bank don't have enough information
all the time.

If you'd like to use this approach, you could setup a program like [Macro
Droid](https://play.google.com/store/search?q=macro%20droid&c=apps&hl=en_IN&gl=US)
or
[Tasker](https://play.google.com/store/apps/details?id=net.dinglisch.android.taskerm&hl=en_IN&gl=US)
to update a text file on your phone, each time a new (transactional) SMS
arrives. You could then write a parser for this SMS messages file.

Or use something like the [Android Incoming SMS Gateway
Webhook](https://github.com/bogkonstantin/android_income_sms_gateway_webhook)
that sends each text message to a Webhook as it arrives. You could write a
webhook that captures the SMS text, parses it and writes it to the DB.

### Cash transactions

You could use a simple Google Form to track Cash expenses that are not captured
digitally.  You can make a copy of this [Sample
form](https://docs.google.com/spreadsheets/d/1LWoj0L-OkYOJXmz8jmxMpUJ0kBIWuDSt_TqUisAXt-I/edit#gid=1684157822)
from `File > Make a copy` and then use the copied form (`Tools > Manage Form >
Go to live form`) to fill in your data. You can set the `GSHEET_ID` environment
variable to the ID of the spreadsheet after setting the permissions to make the
sheet viewable by anyone with the link.  The script `gdrive-csv.py` can then be
used to fetch this data as a CSV.

### User defined Categories

The app itself provides a small list of categories and allows users to define
their own list of categories. New categories can be added to the list of
`EXTRA_CATEGORIES` list in `conf.py` placed at the root of the project.  You
can copy `sample-conf.py` as `conf.py` and edit it.

## Installation

- If you use `poetry`, you could just run `poetry install`.

- If you prefer `pip`, you could run `pip install -r requirements.txt` inside a
  virtualenv.

## Running the code

- To setup the DB correctly, run `alembic upgrade head`.

- The `axis-scraper.py` uses `seleniumbase` plugin for `pytest` to scrape the
  data. This lets us configure re-runs when the scraping sometimes fails due to
  network errors, etc. It also lets us run the Credit card transactions scraper
  in parallel with the account transactions scraper.

  To run the scraper:

  ```bash
  pytest -sv ./scripts/axis-scraper.py --browser=firefox --workers=2 --reruns=5 --reruns-delay=20 --archive-downloads
  ```

- Once the data has been downloaded, the `parse-data.py` can be used to parse
  it and save it into the DB.

  ```bash
  python ./scripts/parse-data.py ./downloaded_files/xxx.csv
  ```

- To visualize the data in the DB, you can run the `streamlit` app:

  ```bash
  streamlit run app/app.py
  ```

Look at the scripts `update.sh` and `run-sample.sh` for examples of how to run
the scripts described above.

## Sample data and UI

- The repo contains some sample data for writing the parsers, tests and testing
  out the UI.

- Once the dependencies have been installed you can simply run the
  `scripts/run-sample.sh` script to see the sample data visualized.


## Features

- Visualize expenses
  - Filter expenses by time duration (month, year or complete duration)
    - View barcharts of expenses by day of month
    - View barcharts of expenses by day of week
  - Filter by categories for expenses
- Mark transactions as ignored transactions from the UI
- Assign one or more categories for transactions from the UI
- Add remarks on transactions
- Edit merchant (counterparty) names from the UI, since data from Banks usually
  truncates names.

### To be implemented/ideas

- Automatically add categories for similar transactions
- Mark some transactions as repayment for another transaction. Useful when
  splitting a bill after you have paid it.
- Filter by counterparty name

### Screenshot

![Latest Screenshot](/latest-screenshot.png "Latest Screenshot with Sample DB")
