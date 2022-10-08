# Standard library
import calendar
import datetime
import os
from pathlib import Path

# 3rd party libs
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# Local
from model import Expense

DATE_FMT = "%d %b '%y"
WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
DB_NAME = os.getenv("EXPENSES_DB", "expenses.db")


def remove_ignore_rows(data):
    # FIXME: Make these configurable? Or may be just mark them in the UI and
    # store as different column
    credit_card_payments = ("CreditCard Payment", "MB PAYMENT #")
    details = data["details"].str
    self_payments = "/PUNEETH H/State Ban/"
    return data[
        ~details.startswith(credit_card_payments) & ~details.contains(self_payments)
    ]


def get_db_url():
    here = Path(__file__).parent.parent
    db_path = here.joinpath(DB_NAME)
    return f"sqlite:///{db_path}"


@st.experimental_singleton
def get_db_engine():
    return create_engine(get_db_url())


@st.experimental_singleton
def get_sqlalchemy_session():
    engine = get_db_engine()
    Session = sessionmaker(bind=engine)
    return Session()


@st.experimental_memo
def last_updated():
    engine = get_db_engine()
    (date,) = engine.execute("SELECT MAX(date) FROM expenses").fetchone()
    date, _ = date.split()
    return date


@st.experimental_memo
def load_data(start_date, end_date):
    engine = get_db_engine()
    sql = (
        f"SELECT * FROM expenses WHERE date >= '{start_date}' AND date <= '{end_date}'"
    )
    data = pd.read_sql_query(sql, engine, parse_dates=["date"], dtype={"ignore": bool})
    data = remove_ignore_rows(data)
    return data.sort_values(by=["date"], ignore_index=True, ascending=False)


@st.experimental_memo
def get_months():
    engine = get_db_engine()
    sql = f"SELECT date FROM expenses"
    data = pd.read_sql_query(sql, engine, parse_dates=["date"])
    months = sorted(set(data["date"].apply(lambda x: (x.year, x.month))), reverse=True)
    return months


def format_month(month):
    return datetime.date(*(month + (1,))).strftime("%b, '%y")


def set_ignore_value(row, value):
    session = get_sqlalchemy_session()
    row["ignore"] = value
    id_ = row["id"]
    expense = session.query(Expense).get({"id": id_})
    expense.ignore = value
    session.commit()


def display_transaction(row, n, data_columns):
    columns = st.columns(n)
    id = row["id"]
    for idx, name in enumerate(data_columns):
        value = row.get(name)
        written = False
        if name == "ignore":
            ignore_value = columns[idx].checkbox("", value=value, key=f"ignore-{id}")
            written = True
            if ignore_value != value:
                set_ignore_value(row, ignore_value)

        elif name == "date":
            value = f"{value.strftime(DATE_FMT)}"
        elif name == "amount":
            value = f"{value:.2f}"

        if not written:
            columns[idx].write(value)


def delta_percent(curr, prev):
    if prev == 0:
        return 100
    else:
        return (curr - prev) * 100 / prev


def display_transactions(data, prev_data):
    col1, col2 = st.columns(2)
    total = data["amount"].sum()
    prev_total = prev_data["amount"].sum()
    delta = f"{delta_percent(total, prev_total):.2f} %"
    max_ = data["amount"].max()
    col1.metric("Total Spend", f"₹ {total:.2f}", delta=delta, delta_color="inverse")
    col2.metric("Maximum Spend", f"₹ {max_:.2f}")
    n = len(data)

    with st.expander(f"Total {n} transactions", expanded=True):
        n = [1, 1, 10, 1]
        data_columns = ["date", "amount", "details", "ignore"]
        headers = st.columns(n)
        for idx, name in enumerate(data_columns):
            headers[idx].write(f"**{name.title()}**")
        data.apply(display_transaction, axis=1, n=n, data_columns=data_columns)


def display_sidebar(title):
    with st.sidebar:
        st.title(title)
        months = get_months()
        option = st.selectbox("Select Month to view", months, format_func=format_month)
        start_date = datetime.datetime(*option + (1,))
        _, num_days = calendar.monthrange(*option)
        end_date = datetime.datetime(*option + (num_days,))

        # Add a note about the last updated date
        updated = last_updated()
        st.caption(f"Expense data last updated on {updated}")

    return start_date, end_date


def previous_month(start_date):
    end_ = start_date - datetime.timedelta(days=1)
    start = datetime.date(end_.year, end_.month, 1)
    return start, end_


def display_barcharts(data):
    # Show bar chart by day of month
    groups = data.groupby(by=lambda idx: data.iloc[idx]["date"].day)
    st.bar_chart(groups.sum(["amount"]))

    # Show bar chart by weekday
    weekday_amounts = (
        data.groupby(by=lambda idx: data.iloc[idx]["date"].day_name())
        .sum(["amount"])
        .reset_index(names="weekdays")
        .sort_values(by="weekdays", key=lambda x: [WEEKDAYS.index(e) for e in x])
    )
    # Weird code for turning off x-axis sorting based on
    # https://discuss.streamlit.io/t/sort-the-bar-chart-in-descending-order/1037/2
    st.altair_chart(
        alt.Chart(weekday_amounts)
        .mark_bar()
        .encode(x=alt.X("weekdays", sort=None), y="amount"),
        use_container_width=True,
    )


def main():
    title = "Personal Expense Tracker"

    st.set_page_config(
        page_title=title,
        page_icon=":bar-chart:",
        layout="wide",
        initial_sidebar_state="auto",
        menu_items={
            "Get Help": "https://github.com/punchagan/expense-tracker/issues",
            "Report a bug": "https://github.com/punchagan/expense-tracker/issues",
        },
    )

    start_date, end_date = display_sidebar(title)
    data = load_data(start_date, end_date)

    prev_start, prev_end = previous_month(start_date)
    prev_data = load_data(prev_start, prev_end)

    display_barcharts(data)
    display_transactions(data, prev_data)


if __name__ == "__main__":
    main()
