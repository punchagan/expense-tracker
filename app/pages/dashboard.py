# Standard library
import datetime
import json
import os
import sys
from pathlib import Path

# 3rd party libs
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from sqlalchemy import bindparam, text
from sqlalchemy.orm import sessionmaker

# Local
from app.components.git_status import check_git_status
from app.db_util import (
    DB_PATH,
    get_db_engine,
    sync_db_with_data_repo,
    update_similar_counterparty_categories,
    update_similar_counterparty_names,
    set_tags_value,
)
from app.model import Category, Expense, Tag
from app.util import daterange_from_year_month, delta_percent, format_month, previous_month

# Enable Pandas copy-on-write
pd.options.mode.copy_on_write = True

DATE_FMT = "%d %b '%y"
WEEKDAYS = [datetime.date(2001, 1, i).strftime("%A") for i in range(1, 8)]
HERE = Path(__file__).parent
ROOT = HERE.parent
ALL_TAG = ALL_CATEGORY = 0
NO_TAG = NO_CATEGORY = -1
DATA_COLUMNS = [
    "date",
    "counterparty_name",
    "amount",
    "remarks",
    "category_id",
    "tags",
    "parent",
    "ignore",
]
CURRENCY_SYMBOL = "₹"


@st.cache_resource
def get_sqlalchemy_session():
    engine = get_db_engine()
    Session = sessionmaker(bind=engine)
    return Session()


@st.cache_data
def last_updated():
    engine = get_db_engine()
    with engine.connect() as conn:
        (date,) = conn.execute(text("SELECT MAX(date) FROM expense")).fetchone()
    date, _ = date.split() if date else (None, None)
    return date


@st.cache_data
def load_data(start_date, end_date, category, db_last_modified):
    # NOTE: db_last_modified is only used to invalidate the memoized data
    print(f"DB last modified at: {db_last_modified}")
    engine = get_db_engine()
    category_clause = (
        "AND e.category_id=:category"
        if category not in {NO_CATEGORY, ALL_CATEGORY}
        else ("AND e.category_id IS NULL" if category == NO_CATEGORY else "")
    )
    base_sql = f"""
    SELECT e.*, JSON_GROUP_ARRAY(et.tag_id) AS tags
    FROM expense e
    LEFT JOIN expense_tag et ON e.id = et.expense_id
    """
    filter_sql = f"""WHERE e.date >= :start_date AND e.date < :end_date
    AND (e.parent IS NULL OR e.parent = '')
    {category_clause}
    GROUP BY e.id;
    """
    params = dict(start_date=start_date, end_date=end_date)
    if category not in {NO_CATEGORY, ALL_CATEGORY}:
        params["category"] = category
    sql = text(f"{base_sql} {filter_sql}").bindparams(**params)
    dtype = {"ignore": bool, "category_id": "Int64", "reviewed": bool}
    data = pd.read_sql_query(sql, engine, parse_dates=["date"], dtype=dtype)
    parents = tuple(set(data["id"]))
    if parents:
        child_sql = text(f"{base_sql} WHERE e.parent IN :parents GROUP BY e.id").bindparams(
            bindparam("parents", value=parents, expanding=True)
        )
        children = pd.read_sql_query(child_sql, engine, parse_dates=["date"], dtype=dtype)
        if not children.empty:
            data = pd.concat([data, children])
    data.fillna({"category_id": NO_CATEGORY}, inplace=True)
    data.fillna({"parent": ""}, inplace=True)
    data.counterparty_name = (
        data.counterparty_name.replace("None", "")
        .fillna("")
        .apply(lambda x: x if x is not None else "")
    )
    data.remarks = (
        data.remarks.replace("None", "").fillna("").apply(lambda x: x if x is not None else "")
    )
    data.tags = data.tags.apply(lambda x: list(filter(None, json.loads(x))))
    return data


@st.cache_data
def get_categories():
    session = get_sqlalchemy_session()
    categories = session.query(Category).order_by("id").all()
    return {cat.id: cat for cat in categories}


@st.cache_data
def get_tags():
    session = get_sqlalchemy_session()
    tags = session.query(Tag).order_by("id").all()
    return {tag.id: tag for tag in tags}


@st.cache_data
def get_months():
    engine = get_db_engine()
    sql = f"SELECT date FROM expense"
    data = pd.read_sql_query(sql, engine, parse_dates=["date"])
    months = set(data["date"].apply(lambda x: (x.year, x.month)))
    years = {(y, 13) for (y, _) in months}
    months = sorted(months.union(years), reverse=True)
    return [(0, 13)] + months


def mark_expenses_as_reviewed(expense_ids):
    session = get_sqlalchemy_session()
    expenses = session.query(Expense)
    if expense_ids:
        expenses = expenses.filter(Expense.id.in_(expense_ids))
    expenses.update({"reviewed": True}, synchronize_session=False)
    session.commit()
    st.rerun()


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


def write_changes_to_db(df):
    # Find the changes
    changes = st.session_state["expenses_data"]["edited_rows"]

    for idx, change in changes.items():
        row = df.iloc[idx]
        # Fetch the expense from the DB
        session = get_sqlalchemy_session()
        expense = session.get(Expense, {"id": row["id"]})

        for key, value in change.items():
            if key == "counterparty_name" and value.endswith("**"):
                name = value.strip("*")
                update_similar_counterparty_names(session, expense, name)
            elif key == "category_id":
                categories = get_categories()
                update_similar_counterparty_categories(session, expense, value, categories)
            elif key == "tags":
                tags = get_tags()
                set_tags_value(expense, value, tags)
            elif key == "parent":
                parent_id = value
                if value is not None:
                    parent_id = value.split(":::")[-1]
                    if not parent_id or parent_id == expense.id:
                        parent_id = None
                setattr(expense, key, parent_id)
            else:
                setattr(expense, key, value)

        if change:
            expense.reviewed = True

    if changes:
        session.commit()


@st.fragment
def display_summary_stats(data, prev_data):
    col1, col2 = st.columns(2)
    data_clean = remove_ignored_rows(data)
    prev_data_clean = remove_ignored_rows(prev_data)
    total = data_clean["amount"].sum()
    prev_total = prev_data_clean["amount"].sum()
    delta = delta_percent(total, prev_total)
    max_ = data_clean["amount"].max() if len(data_clean) > 0 else 0
    col1.metric(
        "Total Spend",
        f"{CURRENCY_SYMBOL} {total:.2f}",
        delta=delta,
        delta_color="inverse",
    )
    col2.metric("Maximum Spend", f"{CURRENCY_SYMBOL} {max_:.2f}")


def format_column_name(name):
    name = name.replace("_id", "").replace("_", " ")
    return f"**{name.title()}**"


def display_transactions(data, categories, tags):
    data_clean = remove_ignored_rows(data)
    m = len(data[data.category_id == NO_CATEGORY])

    n = len(data)
    nc = len(data_clean)
    page_size = 20
    paginate = len(data_clean) > 2 * page_size

    with st.expander(f"Total {n} transactions ({m} uncategorized)", expanded=True):
        knob1, knob2, knob3 = st.columns([2, 2, 1])
        sort_column = knob1.radio(
            label="Sort Transactions by ...",
            index=1,
            options=["date", "amount", "num. of transactions"],
            horizontal=True,
        )
        hide_ignored_transactions = knob1.checkbox(label="Hide Ignored Transactions")
        show_only_unreviewed = knob1.checkbox(label="Show Only Unreviewed")
        show_all = not paginate or knob3.checkbox(label="Turn off pagination")
        if paginate:
            count = n if not hide_ignored_transactions else nc
            max_value = count // page_size + 1
            page_number = knob3.number_input(
                "Page number", min_value=1, max_value=max_value, disabled=show_all
            )
        knob2.write(
            """
- Counterparty names support a bulk editing mode. Any transactions (parsed from the same source) with a similar name can be changed to a new name by entering a new name ending with two `*`. For instance, `Swiggy**`.
- Parent for a transaction can be set from the Details View.
        """.strip()
        )

        df = data_clean if hide_ignored_transactions else data
        df = df if not show_only_unreviewed else df[df.reviewed == False]
        sort_orders = {"ignore": True}
        if sort_column == "date":
            sort_by = ["ignore", "date", "amount", "details"]
        elif sort_column == "amount":
            sort_by = ["ignore", "amount", "date", "details"]
        else:
            # number of transactions
            counts = data.counterparty_name.value_counts()
            data["counts"] = data.apply(lambda row: counts[row.counterparty_name], axis=1)
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
        no_parent_rows = df["parent"].str.len() > 0
        parent_df = df[~no_parent_rows].reset_index(drop=True)
        page_df = (
            parent_df
            if show_all
            else parent_df[page_size * (page_number - 1) : page_size * page_number]
        )
        child_df = df[df.parent.isin(page_df.id)]
        ids = parent_df.id.to_list()
        child_df.index = child_df.apply(lambda row: ids.index(row["parent"]) + 0.1, axis=1)
        if not child_df.empty:
            page_df = pd.concat([page_df, child_df])

        # Transform the data for display
        page_df["category_id"] = page_df["category_id"].apply(
            lambda x: format_category(x, categories)
        )
        # FIXME: Just use the first tag until we switch to ListColumn
        all_tags = get_tags()
        page_df["tags"] = page_df["tags"].apply(lambda tags: all_tags[tags[0]].name if tags else "")
        # Add the parent transaction details to the child transactions
        session = get_sqlalchemy_session()
        parents = session.query(Expense).filter(Expense.id.in_(page_df["parent"])).all()
        parents_map = {exp.id: exp for exp in parents}
        page_df["parent"] = page_df["parent"].apply(
            lambda pid: format_row(parents_map[pid].__dict__) if pid else None
        )
        st.data_editor(
            page_df,
            column_config={
                "date": st.column_config.DateColumn(
                    "Date", format="DD MMM 'YY", help="Date of the transaction."
                ),
                "counterparty_name": st.column_config.TextColumn(
                    "Counterparty", help="The name of the counterparty"
                ),
                "amount": st.column_config.NumberColumn(
                    "Amount", format="%.2f", help="The amount of the transaction"
                ),
                "remarks": st.column_config.TextColumn(
                    "Details", help="Details of the transaction"
                ),
                "ignore": st.column_config.CheckboxColumn(
                    "Ignore",
                    help="Ignore this transaction in the summary stats and visualizations",
                ),
                "category_id": st.column_config.SelectboxColumn(
                    "Category",
                    help="The category of the transaction",
                    options=[cat.name for cat in categories.values()],
                    required=False,
                ),
                "parent": st.column_config.SelectboxColumn(
                    "Parent",
                    help=(
                        "Choose a parent transaction for the current transaction."
                        "\n\n Only the transactions that are part of the current view"
                        "(year/month/category/amount range/etc.) are shown. "
                        "**Change the filters if your required transaction is not visible.**"
                    ),
                    # NOTE: We use all the transactions of the current filtered
                    # view as options, since the parent may not be in the
                    # current page. Also, to keep the UI fast, we don't try to
                    # any smart filtering of options to remove invalid ones
                    # (like transaction can't be it's own parent, etc.)
                    options=page_df.apply(format_row, axis=1),
                    required=False,
                ),
                # FIXME: use ListColumn when it becomes editable
                # See https://github.com/streamlit/streamlit/pull/9223
                "tags": st.column_config.SelectboxColumn(
                    "Tags",
                    help="The tags of the transaction. (Note: Currently, only one tag is supported)",
                    options=[tag.name for tag in tags.values()],
                    required=False,
                ),
            },
            key="expenses_data",
            on_change=write_changes_to_db,
            args=(page_df,),
            use_container_width=True,
            column_order=DATA_COLUMNS,
            disabled=["date", "amount"],
            hide_index=True,
        )

        _, r3, r2, r1 = st.columns([3, 1, 1, 1])
        mark_page_reviewed = r1.button(
            "Mark Page Reviewed",
            key=f"mark-page-reviewed",
            help="Mark all transactions in the current page as reviewed",
            disabled=show_all,
        )
        if mark_page_reviewed:
            ids = list(page_df.id)
            mark_expenses_as_reviewed(ids)

        mark_filter_reviewed = r2.button(
            "Mark Filtered Reviewed",
            key=f"mark-filtered-reviewed",
            help="Mark all transactions in the currently filtered view as reviewed",
        )
        if mark_filter_reviewed:
            ids = list(df.id)
            mark_expenses_as_reviewed(ids)

        mark_all_reviewed = r3.button(
            "Mark *All* Reviewed",
            key=f"mark-all-reviewed",
            help="Mark all transactions in the DB as reviewed",
        )
        if mark_all_reviewed:
            mark_expenses_as_reviewed([])


def format_amount(amount):
    amount = (
        "-∞"
        if np.isneginf(amount)
        else "∞" if np.isposinf(amount) else f"{CURRENCY_SYMBOL} {amount}"
    )
    return amount


def display_extra_filters(data, tags, disabled):
    counterparties = ["All"] + sorted(set(data["counterparty_name"]) - set([""]))
    tag_ids = sorted({tag for tags in data.tags for tag in tags})
    options = (-np.inf, 0, 1000, 5000, 10000, 20000, np.inf)
    with st.sidebar:
        counterparty = st.selectbox(
            "Counter Party", counterparties, disabled=disabled, key=f"cp-filter"
        )
        selected_tags = st.multiselect(
            label="Tags",
            options=tag_ids,
            default=[],
            key=f"tag-filter",
            format_func=lambda x: format_tag(x, tags),
            disabled=disabled,
        )
        start, end = st.select_slider(
            label="Amount",
            options=options,
            value=(options[0], options[-1]),
            format_func=format_amount,
            key="amount-filter",
            disabled=disabled,
        )
    return counterparty, selected_tags, (start, end)


def display_sidebar(title, categories, disabled):
    with st.sidebar:
        st.title(title)
        st.caption(
            "A UI to annotate and visualize personal expenses captured from different sources."
        )

        st.caption(st.secrets.get("cloud_note", ""))

        # Add a note about the last updated date
        updated = last_updated()
        st.caption(f"*Expense data last updated on {updated}*")

        months = get_months()
        option = st.selectbox(
            "Time Period",
            months,
            format_func=format_month,
            index=min(2, len(months) - 1),
            disabled=disabled,
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
    day_data = data.pivot_table(index="day", columns="category", values="amount", aggfunc="sum")
    col1.bar_chart(day_data)

    weekday_data = data.sort_values(by="weekday", key=lambda x: [WEEKDAYS.index(e) for e in x])
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
    category_data.index = [format_category(idx, categories) for idx in category_data.index]

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
    return f"{row['date']:%Y-%m-%d} — {row['amount']:.2f} — {row['details']}:::{row['id']}"


def dashboard():
    title = "Personal Expense Tracker"

    st.set_page_config(
        page_title=title,
        page_icon=":bar-chart:",
        layout="wide",
        initial_sidebar_state="auto",
        menu_items={
            "About": "Source code on [GitHub](https://github.com/punchagan/expense-tracker/) :tada:",
            "Get Help": "https://github.com/punchagan/expense-tracker/issues",
            "Report a bug": "https://github.com/punchagan/expense-tracker/issues",
        },
    )

    git_manager = check_git_status()
    if git_manager is None:
        st.switch_page("pages/data_management.py")

    if git_manager.is_dirty():
        st.warning("You have uncommitted changes in your data repository.")

    # Sync DB with dump in git DATA repo
    sync_db_with_data_repo()

    # db_last_modified is used to detect DB changes and invalidate Streamlit
    # memoized data
    db_last_modified = os.path.getmtime(DB_PATH)

    categories = get_categories()
    tags = get_tags()
    start_date, end_date, category = display_sidebar(title, categories, disabled=False)
    data = load_data(start_date, end_date, category, db_last_modified)

    prev_start, prev_end = previous_month(start_date)
    prev_data = load_data(prev_start, prev_end, category, db_last_modified)
    counterparty, selected_tags, (low, high) = display_extra_filters(data, tags, disabled=False)

    if counterparty != "All":
        data = data[data["counterparty_name"] == counterparty]
        prev_data = prev_data[prev_data["counterparty_name"] == counterparty]

    if selected_tags:
        tag_filter = lambda x: bool(set(x).intersection(selected_tags))
        data = data[data.tags.apply(tag_filter)]
        prev_data = prev_data[prev_data.tags.apply(tag_filter)]

    def amount_filter_low(data, low):
        return data[(data.amount >= low) | (data.parent.str.len() > 0)]

    def amount_filter_high(data, high):
        return data[(data.amount <= high) | (data.parent.str.len() > 0)]

    if not np.isneginf(low):
        data = amount_filter_low(data, low)
        prev_data = amount_filter_low(prev_data, low)

    if not np.isposinf(high):
        data = amount_filter_high(data, high)
        prev_data = amount_filter_high(prev_data, high)

    display_summary_stats(data, prev_data)
    display_barcharts(data, categories, tags)
    display_transactions(data, categories, tags)


dashboard()
