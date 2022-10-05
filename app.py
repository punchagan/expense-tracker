# Standard library
import calendar
import datetime
from pathlib import Path

# 3rd party libs
from sqlalchemy import create_engine
import streamlit as st
import pandas as pd
import numpy as np

DATE_FMT = "%d %b '%y"


def remove_ignore_rows(data):
    # FIXME: Make these configurable? Or may be just mark them in the UI and
    # store as different column
    credit_card_payments = ("CreditCard Payment", "MB PAYMENT #")
    details = data["details"].str
    self_payments = "/PUNEETH H/State Ban/"
    return data[
        ~details.startswith(credit_card_payments) & ~details.contains(self_payments)
    ]


def get_db_engine():
    here = Path(__file__).parent
    db_path = here.joinpath("expenses.db")
    return create_engine(f"sqlite:///{db_path}")


@st.cache
def last_updated():
    engine = get_db_engine()
    (date,) = engine.execute("SELECT MAX(date) FROM expenses").fetchone()
    date, _ = date.split()
    return date


@st.cache
def load_data(start_date, end_date):
    engine = get_db_engine()
    sql = (
        f"SELECT * FROM expenses WHERE date >= '{start_date}' AND date <= '{end_date}'"
    )
    data = pd.read_sql_query(sql, engine, parse_dates=["date"])
    data = remove_ignore_rows(data)
    return data.sort_values(by=["date"], ignore_index=True, ascending=False)


@st.cache
def get_months():
    engine = get_db_engine()
    sql = f"SELECT date FROM expenses"
    data = pd.read_sql_query(sql, engine, parse_dates=["date"])
    months = sorted(set(data["date"].apply(lambda x: (x.year, x.month))), reverse=True)
    return months


def format_month(month):
    return datetime.date(*(month + (1,))).strftime("%b, '%y")


def display_transaction(row, n, data_columns):
    columns = st.columns(n)
    for idx, name in enumerate(data_columns):
        value = row[name]
        if name == "date":
            value = f"{value.strftime(DATE_FMT)}"
        elif name == "amount":
            value = f"{value:.2f}"
        columns[idx].write(value)


def display_transactions(data, start_date, end_date):
    col1, col2 = st.columns(2)
    total = data["amount"].sum()
    max_ = data["amount"].max()
    col1.metric("Total Spend", f"₹ {total:.2f}")
    col2.metric("Maximum Spend", f"₹ {max_:.2f}")
    n = len(data)

    with st.expander(f"View {n} transactions", expanded=True):
        n = 3
        data_columns = ["date", "amount", "details"]
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


def main():
    title = "Personal Expense Tracker"

    st.set_page_config(
        page_title=title,
        page_icon=":bar-chart:",
        layout="wide",
        initial_sidebar_state="auto",
        menu_items=None,
    )

    start_date, end_date = display_sidebar(title)
    data = load_data(start_date, end_date)
    display_transactions(data, start_date, end_date)


if __name__ == "__main__":
    main()
