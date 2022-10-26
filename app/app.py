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
from app.data import CATEGORIES, create_categories, create_tags
from app.model import Category, Expense, Tag
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
ALL_TAG = ALL_CATEGORY = 0
NO_TAG = NO_CATEGORY = -1
DATA_COLUMNS = [
    "ignore",
    "date",
    "amount",
    "counterparty_name",
    "category_id",
    "tags",
    "remarks",
    "details",
]


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


@st.experimental_memo
def ensure_tags_created():
    session = get_sqlalchemy_session()
    try:
        from conf import TAGS as tags
    except ImportError:
        tags = []
    return create_tags(session, tags)


@st.experimental_memo
def load_data(start_date, end_date, category, db_last_modified):
    # NOTE: db_last_modified is only used to invalidate the memoized data
    engine = get_db_engine()
    category_clause = (
        f"AND e.category_id = {category}"
        if category not in {NO_CATEGORY, ALL_CATEGORY}
        else ("AND e.category_id IS NULL" if category == NO_CATEGORY else "")
    )
    base_sql = f"""
    SELECT e.*, JSON_GROUP_ARRAY(et.tag_id) AS tags
    FROM expense e
    LEFT JOIN expense_tag et ON e.id = et.expense_id
    """
    filter_sql = f"""WHERE e.date >= '{start_date}' AND e.date < '{end_date}'
    AND e.parent IS NULL OR e.parent = ''
    {category_clause}
    GROUP BY e.id;
    """
    sql = f"{base_sql} {filter_sql}"
    dtype = {"ignore": bool, "category_id": "Int64"}
    data = pd.read_sql_query(sql, engine, parse_dates=["date"], dtype=dtype)
    parents = tuple(set(data["id"]))
    child_sql = f"""{base_sql} WHERE e.parent IN {parents} GROUP BY e.id"""
    children = pd.read_sql_query(child_sql, engine, parse_dates=["date"], dtype=dtype)
    data = pd.concat([data, children])
    data.category_id.fillna(NO_CATEGORY, inplace=True)
    data.parent.fillna("", inplace=True)
    data.counterparty_name = (
        data.counterparty_name.replace("None", "")
        .fillna("")
        .apply(lambda x: x if x is not None else "")
    )
    data.remarks = (
        data.remarks.replace("None", "")
        .fillna("")
        .apply(lambda x: x if x is not None else "")
    )
    data.tags = data.tags.apply(lambda x: list(filter(None, json.loads(x))))
    return data


@st.experimental_memo
def get_categories():
    session = get_sqlalchemy_session()
    categories = session.query(Category).order_by("id").all()
    return {cat.id: cat for cat in categories}


@st.experimental_memo
def get_tags():
    session = get_sqlalchemy_session()
    tags = session.query(Tag).order_by("id").all()
    return {tag.id: tag for tag in tags}


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


def update_similar_counterparty_names(row, name):
    engine = get_db_engine()
    parsed_name = row["counterparty_name_p"]
    source = row["source"]
    query = (
        f"UPDATE expense SET counterparty_name = '{name}' "
        f" WHERE counterparty_name_p = '{parsed_name}' AND source = '{source}'"
    )
    engine.execute(query)
    st.experimental_rerun()


def update_similar_counterparty_categories(row, category_id):
    engine = get_db_engine()
    name = row["counterparty_name"]
    category_id = "NULL" if category_id == NO_CATEGORY else str(category_id)
    parent_id = row["parent"]
    row_id = row["id"]
    query = f"""
    UPDATE expense SET category_id = {category_id}
    WHERE counterparty_name = '{name}' OR parent = '{row_id}' OR id = '{parent_id}'
    """
    engine.execute(query)
    st.experimental_rerun()


def set_tags_value(row, tags, all_tags):
    session = get_sqlalchemy_session()
    id_ = row["id"]
    expense = session.query(Expense).get({"id": id_})

    old_tags = {tag.id: tag for tag in expense.tags}
    old_ids = set(old_tags)
    new_ids = set(tags)

    removed = old_ids - new_ids
    for old_id, tag in old_tags.items():
        if old_id in removed:
            expense.tags.remove(tag)

    added = new_ids - old_ids
    for tag_id in added:
        expense.tags.append(all_tags[tag_id])

    session.commit()
    st.experimental_rerun()


def format_category(category_id, categories):
    if category_id == NO_CATEGORY:
        return "Uncategorized"
    elif category_id == ALL_CATEGORY:
        return "All"
    return categories[category_id].name


def format_tag(tag_id, tags):
    if tag_id == NO_TAG:
        return "Untagged"
    elif tag_id == ALL_TAG:
        return "All"
    return tags[tag_id].name


def display_transaction(row, n, data_columns, categories, tags):
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
        elif name == "category_id":
            options = [NO_CATEGORY] + sorted(categories)
            category_id = col.selectbox(
                label="Category",
                options=options,
                index=options.index(value),
                key=f"category-{id}",
                label_visibility="collapsed",
                format_func=lambda x: format_category(x, categories),
            )
            if category_id != value:
                update_similar_counterparty_categories(row, category_id)
            written = True
        elif name == "tags":
            options = sorted(tags)
            selected = col.multiselect(
                label="Tags",
                options=options,
                default=value,
                key=f"tag-{id}",
                label_visibility="collapsed",
                format_func=lambda x: format_tag(x, tags),
            )
            if sorted(selected) != sorted(value):
                set_tags_value(row, selected, all_tags=tags)
            written = True
        elif name == "details":
            written = True
            show_details = col.button("Details", key=f"details-{id}")
            if show_details:
                st.session_state.transaction_id = row["id"]
                st.experimental_rerun()
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
                    update_similar_counterparty_names(row, new_value)
                else:
                    set_column_value(row, name, new_value)
        elif name == "date":
            value = f"{value.strftime(DATE_FMT)}"
            if row["parent"]:
                value = f"*{value}*"
        elif name == "amount":
            value = f"{value:.2f}"
            if row["parent"]:
                value = f"*{value}*"

        if not written:
            col.write(value)

    return show_details


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


def format_column_name(name):
    name = name.replace("_id", "").replace("_", " ")
    return f"**{name.title()}**"


def display_transactions(data, categories, tags):
    n = len(data)
    data_clean = remove_ignored_rows(data)
    with st.expander(f"Total {n} transactions", expanded=True):
        n = [1, 1, 1, 3, 2, 3, 3, 1]
        data_columns = DATA_COLUMNS
        knob1, knob2 = st.columns(2)
        sort_column = knob1.radio(
            label="Sort Transactions by ...",
            options=["date", "amount", "num. of transactions"],
            horizontal=True,
        )
        hide_ignored_transactions = knob2.checkbox(label="Hide Ignored Transactions")

        headers = st.columns(n)
        for idx, name in enumerate(data_columns):
            headers[idx].write(format_column_name(name))
        df = data_clean if hide_ignored_transactions else data
        sort_orders = {"ignore": True}
        if sort_column == "date":
            sort_by = ["ignore", "date", "amount", "details"]
        elif sort_column == "amount":
            sort_by = ["ignore", "amount", "date", "details"]
        else:
            # number of transactions
            counts = data.counterparty_name.value_counts()
            data["counts"] = data.apply(
                lambda row: counts[row.counterparty_name], axis=1
            )
            sort_by = [
                "ignore",
                "counts",
                "counterparty_name",
                "amount",
                "date",
                "details",
            ]
        ascending = [sort_orders.get(name, False) for name in sort_by]
        df = df.sort_values(by=sort_by, ignore_index=True, ascending=ascending)
        child_rows = df["parent"].str.len() > 0
        pdf = df[~child_rows].reset_index(drop=True)
        cdf = df[child_rows]
        ids = pdf.id.to_list()
        cdf.index = cdf.apply(lambda row: ids.index(row["parent"]) + 0.1, axis=1)
        pd.concat([pdf, cdf]).sort_index().reset_index(drop=True).apply(
            display_transaction,
            axis=1,
            n=n,
            data_columns=data_columns,
            categories=categories,
            tags=tags,
        )


def display_extra_filters(data, tags, disabled):
    counterparties = ["All"] + sorted(set(data["counterparty_name"]) - set([""]))
    tag_ids = sorted({tag for tags in data.tags for tag in tags})
    with st.sidebar:
        counterparty = st.selectbox("Counter Party", counterparties, disabled=disabled)
        selected_tags = st.multiselect(
            label="Tags",
            options=tag_ids,
            default=[],
            key=f"tag-{id}",
            format_func=lambda x: format_tag(x, tags),
            disabled=disabled,
        )

    return counterparty, selected_tags


def display_sidebar(title, categories, disabled):
    with st.sidebar:
        # Add a note about the last updated date
        updated = last_updated()
        st.caption(f"Expense data last updated on {updated}")

        st.title(title)

        months = get_months()
        option = st.selectbox(
            "Time Period", months, format_func=format_month, index=2, disabled=disabled
        )
        start_date, end_date = daterange_from_year_month(*option)

        category_ids = [ALL_CATEGORY, NO_CATEGORY] + sorted(categories.keys())
        category = st.selectbox(
            "Category",
            category_ids,
            format_func=lambda x: format_category(x, categories),
            disabled=disabled,
        )

    return start_date, end_date, category


def remove_ignored_rows(data):
    return data[~data["ignore"]].reset_index(drop=True)


def display_barcharts(data, categories, tags):
    # Filter ignored transactions
    data = remove_ignored_rows(data)

    if len(data) == 0:
        return

    col1, col2 = st.columns([4, 1])

    # Add additional columns for day, weekday and category
    data[["day", "weekday", "category"]] = data.apply(
        lambda row: (
            row["date"].day,
            row["date"].day_name(),
            format_category(row["category_id"], categories),
        ),
        axis=1,
        result_type="expand",
    )
    day_data = data.pivot_table(
        index="day", columns="category", values="amount", aggfunc="sum"
    )
    col1.bar_chart(day_data)

    weekday_data = data.sort_values(
        by="weekday", key=lambda x: [WEEKDAYS.index(e) for e in x]
    )
    col2.altair_chart(
        alt.Chart(weekday_data)
        .mark_bar()
        .encode(x=alt.X("weekday", sort=None), y="sum(amount)", color="category"),
        use_container_width=True,
    )

    # Group data by category
    category_data = data.pivot_table(
        index="category_id", columns="category", values="amount", aggfunc="sum"
    )
    category_data.index = [
        format_category(idx, categories) for idx in category_data.index
    ]

    tag_data = data.explode("tags").pivot_table(
        index="tags", columns="category", values="amount", aggfunc="sum"
    )
    tag_data.index = [format_tag(idx, tags) for idx in tag_data.index]

    n_cat = len(category_data.index)
    n_tag = len(tag_data.index)
    if n_tag + n_cat < 40 and n_tag > 0 and n_cat > 0:
        col1, col2 = st.columns([n_cat, n_tag])
    else:
        col1, col2 = st, st

    if n_cat > 1:
        col1.bar_chart(category_data)

    if n_tag > 1:
        col2.bar_chart(tag_data)
        # FIXME: The colors for categories may be different from the other charts!
        col2.caption("**Note**: colors may be different from the other charts!")


def format_row(row):
    if not row["id"]:
        return "<No Parent>"
    return f"{row['date']} — {row['amount']} — {row['details']}"


def show_transaction_info(row_id, data, categories, tags):
    row = data[data["id"] == row_id].reset_index(drop=True).squeeze()
    col1, col2 = st.columns(2)
    additional_columns = [
        "transaction_type",
        "transaction_id",
        "source",
        "counterparty_bank",
        "parent",
    ]
    for key in DATA_COLUMNS + additional_columns:
        value = row[key]
        if key == "category_id":
            value = format_category(value, categories)
        elif key == "tags":
            value = ", ".join([format_tag(t, tags) for t in value])
        value = "--" if value == "" else value
        col1.write(format_column_name(key))
        if key == "parent":
            old_parent_id = row["parent"]
            df = data[data["amount"] >= np.abs(row["amount"])].reset_index(drop=True)
            options = [{"id": ""}] + df.to_dict(orient="records")
            index = (
                int(df[df["id"] == old_parent_id].index[0]) + 1 if old_parent_id else 0
            )
            parent = col2.selectbox(
                "Select Parent",
                options=options,
                index=index,
                label_visibility="collapsed",
                format_func=format_row,
            )
            if old_parent_id != parent["id"]:
                set_column_value(row, "parent", parent["id"])
        else:
            col2.write(value)
    hide_details = col2.button("Close", key=f"details-{id}")
    if hide_details:
        st.session_state.transaction_id = None
        st.experimental_rerun()


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
    ensure_tags_created()
    tags = get_tags()

    row_id = st.session_state.get("transaction_id")
    display_info = bool(row_id)
    start_date, end_date, category = display_sidebar(title, categories, display_info)
    data = load_data(start_date, end_date, category, db_last_modified)
    prev_start, prev_end = previous_month(start_date)
    prev_data = load_data(prev_start, prev_end, category, db_last_modified)
    counterparty, selected_tags = display_extra_filters(data, tags, display_info)

    if counterparty != "All":
        data = data[data["counterparty_name"] == counterparty]
        prev_data = prev_data[prev_data["counterparty_name"] == counterparty]

    if selected_tags:
        tag_filter = lambda x: bool(set(x).intersection(selected_tags))
        data = data[data.tags.apply(tag_filter)]
        prev_data = prev_data[prev_data.tags.apply(tag_filter)]

    if not display_info:
        display_summary_stats(data, prev_data)
        display_barcharts(data, categories, tags)
        display_transactions(data, categories, tags)
    else:
        show_transaction_info(row_id, data, categories, tags)


if __name__ == "__main__":
    main()
