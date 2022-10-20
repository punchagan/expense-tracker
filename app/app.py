# Standard library
import datetime
import json
import os
from pathlib import Path
import sys

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 3rd party libs
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# Local
from app.data import CATEGORIES, create_categories
from app.model import Category, Expense
from app.util import (
    DB_NAME,
    daterange_from_year_month,
    delta_percent,
    format_month,
    get_db_url,
    previous_month,
)

DATE_FMT = "%d %b '%y"
WEEKDAYS = [datetime.date(2001, 1, i).strftime("%A") for i in range(1, 8)]
HERE = Path(__file__).parent
ROOT = HERE.parent
ALL_CATEGORY = 0


@st.experimental_singleton
def get_db_engine():
    return create_engine(get_db_url())


def get_sqlalchemy_session():
    engine = get_db_engine()
    Session = sessionmaker(bind=engine)
    return Session()


@st.experimental_memo
def last_updated():
    engine = get_db_engine()
    (date,) = engine.execute("SELECT MAX(date) FROM expense").fetchone()
    date, _ = date.split()
    return date


@st.experimental_memo
def ensure_categories_created():
    session = get_sqlalchemy_session()
    try:
        from conf import EXTRA_CATEGORIES

        categories = CATEGORIES + EXTRA_CATEGORIES
    except ImportError:
        categories = CATEGORIES
    return create_categories(session, categories)
    return None


@st.experimental_memo
def load_data(start_date, end_date, category, db_last_modified):
    # NOTE: db_last_modified is only used to invalidate the memoized data
    engine = get_db_engine()
    category_clause = "" if category == ALL_CATEGORY else f"AND c.id = {category}"
    sql = f"""
    SELECT e.*, JSON_GROUP_ARRAY(c.id) AS categories
    FROM expense e
    LEFT JOIN expense_category ec ON e.id = ec.expense_id
    LEFT JOIN category c ON c.id = ec.category_id
    WHERE e.date >= '{start_date}' AND e.date < '{end_date}' {category_clause}
    GROUP BY e.id;
    """
    data = pd.read_sql_query(sql, engine, parse_dates=["date"], dtype={"ignore": bool})
    data.categories = data.categories.apply(lambda x: list(filter(None, json.loads(x))))
    return data


@st.experimental_memo
def get_categories():
    session = get_sqlalchemy_session()
    categories = session.query(Category).order_by("id").all()
    return {cat.id: cat for cat in categories}


@st.experimental_memo
def get_months():
    engine = get_db_engine()
    sql = f"SELECT date FROM expense"
    data = pd.read_sql_query(sql, engine, parse_dates=["date"])
    months = set(data["date"].apply(lambda x: (x.year, x.month)))
    years = {(y, 13) for (y, _) in months}
    months = sorted(months.union(years), reverse=True)
    return [(0, 13)] + months


def set_column_value(row, column_name, value):
    session = get_sqlalchemy_session()
    row[column_name] = value
    id_ = row["id"]
    expense = session.query(Expense).get({"id": id_})
    setattr(expense, column_name, value)
    session.commit()
    st.experimental_rerun()


def update_similar_counterparty_names(row):
    engine = get_db_engine()
    parsed_name = row["counterparty_name_p"]
    name = row["counterparty_name"]
    source = row["source"]
    query = (
        f"UPDATE expense SET counterparty_name = '{name}' "
        f" WHERE counterparty_name_p = '{parsed_name}' AND source = '{source}'"
    )
    engine.execute(query)


def set_categories_value(row, categories, all_categories):
    session = get_sqlalchemy_session()
    id_ = row["id"]
    expense = session.query(Expense).get({"id": id_})

    old_ids = {cat.id for cat in expense.categories}
    new_ids = set(categories)
    removed = old_ids - new_ids
    for category in expense.categories:
        if category.id in removed:
            expense.categories.remove(category)

    added = new_ids - old_ids
    for category_id in added:
        expense.categories.append(all_categories[category_id])

    session.commit()
    st.experimental_rerun()


def format_category(category_id, categories):
    if category_id == ALL_CATEGORY:
        return "All"
    return categories[category_id].name


def display_transaction(row, n, data_columns, categories, sidebar_container):
    columns = st.columns(n)
    id = row["id"]
    for idx, name in enumerate(data_columns):
        value = row.get(name)
        written = False
        col = columns[idx]
        if name == "ignore":
            ignore_value = col.checkbox("", value=value, key=f"ignore-{id}")
            written = True
            if ignore_value != value:
                set_column_value(row, "ignore", ignore_value)
        elif name == "categories":
            selected = col.multiselect(
                label="Categories",
                options=categories,
                default=value,
                key=f"category-{id}",
                label_visibility="collapsed",
                format_func=lambda x: format_category(x, categories),
            )
            if sorted(selected) != sorted(value):
                set_categories_value(row, selected, all_categories=categories)
            written = True
        elif name == "details":
            written = True
            show_details = col.button("Details", key=f"details-{id}")
            if show_details:
                sidebar_container.subheader("Expense Details")
                sidebar_container.dataframe(row)
        elif name in {"remarks", "counterparty_name"}:
            written = True
            new_value = col.text_input(
                name.replace("_", " ").title(),
                value=value,
                label_visibility="collapsed",
                key=f"{name}-{id}",
            )
            if new_value != value:
                if name == "counterparty_name":
                    row["counterparty_name"] = new_value
                    update_similar_counterparty_names(row)
                    st.experimental_rerun()
                else:
                    set_column_value(row, name, new_value)
        elif name == "date":
            value = f"{value.strftime(DATE_FMT)}"
        elif name == "amount":
            value = f"{value:.2f}"

        if not written:
            col.write(value)


def display_summary_stats(data, prev_data):
    col1, col2 = st.columns(2)
    data_clean = remove_ignored_rows(data)
    prev_data_clean = remove_ignored_rows(prev_data)
    total = data_clean["amount"].sum()
    prev_total = prev_data_clean["amount"].sum()
    delta = delta_percent(total, prev_total)
    max_ = data_clean["amount"].max() if len(data_clean) > 0 else 0
    col1.metric("Total Spend", f"₹ {total:.2f}", delta=delta, delta_color="inverse")
    col2.metric("Maximum Spend", f"₹ {max_:.2f}")


def display_transactions(data, categories, sidebar_container):
    n = len(data)
    data_clean = remove_ignored_rows(data)
    with st.expander(f"Total {n} transactions", expanded=True):
        n = [1, 1, 1, 2, 2, 3, 1]
        data_columns = [
            "ignore",
            "date",
            "amount",
            "counterparty_name",
            "remarks",
            "categories",
            "details",
        ]
        hide_ignored_transactions = st.checkbox(label="Hide Ignored Transactions")
        sort_by_amount = st.checkbox(label="Sort Transactions By Amount")
        headers = st.columns(n)
        for idx, name in enumerate(data_columns):
            name = name.replace("_", " ")
            headers[idx].write(f"**{name.title()}**")
        df = data_clean if hide_ignored_transactions else data
        sort_by = (
            ["ignore", "amount", "date", "details"]
            if sort_by_amount
            else ["ignore", "date", "amount", "details"]
        )
        ascending = [True] + [False] * (len(sort_by) - 1)
        df = df.sort_values(by=sort_by, ignore_index=True, ascending=ascending)
        df.apply(
            display_transaction,
            axis=1,
            n=n,
            data_columns=data_columns,
            categories=categories,
            sidebar_container=sidebar_container,
        )


def add_counterparty_filter(sidebar_container, data):
    counterparties = ["All"] + sorted(set(data["counterparty_name"]) - set([""]))
    counterparty = sidebar_container.selectbox("Counter Party", counterparties)
    # Add a note about the last updated date
    updated = last_updated()
    sidebar_container.caption(f"Expense data last updated on {updated}")
    return counterparty


def display_sidebar(title, categories):
    with st.sidebar:
        sidebar_container = st.container()

    sidebar_container.title(title)

    months = get_months()
    option = sidebar_container.selectbox(
        "Time Period", months, format_func=format_month, index=2
    )
    start_date, end_date = daterange_from_year_month(*option)

    category_ids = [0] + sorted(categories.keys())
    category = sidebar_container.selectbox(
        "Category",
        category_ids,
        format_func=lambda x: format_category(x, categories),
    )

    return start_date, end_date, category, sidebar_container


def remove_ignored_rows(data):
    return data[~data["ignore"]].reset_index(drop=True)


def display_barcharts(data):
    # Filter ignored transactions
    data = remove_ignored_rows(data)

    if len(data) == 0:
        return

    # Group data by day of month
    day_groups = data.groupby(by=lambda idx: data.iloc[idx]["date"].day)
    # Group data by weekday
    weekday_amounts = (
        data.groupby(by=lambda idx: data.iloc[idx]["date"].day_name())
        .sum(numeric_only=True)
        .reset_index(names="weekdays")
        .sort_values(by="weekdays", key=lambda x: [WEEKDAYS.index(e) for e in x])
    )

    col1, col2 = st.columns([4, 1])
    col1.bar_chart(day_groups.sum(numeric_only=True)["amount"])
    # Weird code for turning off x-axis sorting based on
    # https://discuss.streamlit.io/t/sort-the-bar-chart-in-descending-order/1037/2
    col2.altair_chart(
        alt.Chart(weekday_amounts)
        .mark_bar()
        .encode(x=alt.X("weekdays", sort=None), y="amount"),
        use_container_width=True,
    )


def local_css(file_name):
    with open(HERE.joinpath(file_name)) as f:
        st.markdown("<style>{}</style>".format(f.read()), unsafe_allow_html=True)


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

    local_css("style.css")
    # Enable Streamlit theme for Altair
    alt.themes.enable("streamlit")

    _, db_path = get_db_url().split("///")
    # Detect DB changes and invalidate Streamlit memoized data
    db_last_modified = os.path.getmtime(db_path)

    ensure_categories_created()
    categories = get_categories()

    start_date, end_date, category, sidebar_container = display_sidebar(
        title, categories
    )
    data = load_data(start_date, end_date, category, db_last_modified)
    prev_start, prev_end = previous_month(start_date)
    prev_data = load_data(prev_start, prev_end, category, db_last_modified)

    counterparty = add_counterparty_filter(sidebar_container, data)

    if counterparty != "All":
        data = data[data["counterparty_name"] == counterparty]
        prev_data = prev_data[prev_data["counterparty_name"] == counterparty]

    display_summary_stats(data, prev_data)
    display_barcharts(data)
    display_transactions(data, categories, sidebar_container)


if __name__ == "__main__":
    main()
