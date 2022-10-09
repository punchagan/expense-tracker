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

But, other scrapers/parsers could be easily written.

Another commonly used approach for tools like this is to parse SMS's sent by
banks to get information about expenses. I considered this approach initially,
but it turned out that that SMS's sent by my bank don't have enough information
all the time. If you'd like to use this approach, you could setup a program
like [Macro
Droid](https://play.google.com/store/search?q=macro%20droid&c=apps&hl=en_IN&gl=US)
or
[Tasker](https://play.google.com/store/apps/details?id=net.dinglisch.android.taskerm&hl=en_IN&gl=US)
to update a text file on your phone, each time a new (transactional) SMS
arrives. You could then write a parser for this SMS messages file.

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

- Visualize expenses by Month
  - View barcharts of expenses by day of month
  - View barcharts of expenses by day of week
- Mark some transactions as to-be ignored (from the UI or a config file)

### To be implemented/ideas

- Choose categories (or tags) for transactions
  - Automatically add categories for similar transactions
  - Multiple tags for a transaction might be useful
- Categorize transactions by type (UPI/CC/AC/etc)
- Mark some transactions as repayment for another transaction, when spending in a group
  - Just grouping a bunch of transactions together might be good?
  - May just be a tag? Or treating them as a single transaction in the UI? :thinking:
- Filter view by Month & Category/Tag or just category/tag
- Filter by transactions made to a particular account/merchant
  - Allow adding full names to account/merchants when full name cannot be
    inferred from downloaded transactions.
- Allow adding comments on transactions, additional notes...
