# Standard library
import datetime
import json
import os
from pathlib import Path
from typing import Any, cast

# 3rd party libs
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from sqlalchemy import bindparam, text
from sqlalchemy.orm.session import Session

# Local
from app.components.git_status import check_git_status
from app.db_util import (
    DB_PATH,
    get_db_engine,
    set_tags_value,
    sync_db_with_data_repo,
    update_similar_counterparty_categories,
    update_similar_counterparty_names,
)
from app.db_util import (
    get_sqlalchemy_session as get_db_session,
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
def get_sqlalchemy_session() -> Session:
    return get_db_session()


@st.cache_data
def last_updated() -> str | None:
    engine = get_db_engine()
    with engine.connect() as conn:
        date_val = conn.execute(text("SELECT MAX(date) FROM expense")).fetchone()
        date = date_val[0] if date_val else None
    date, _ = date.split() if date else (None, None)
    return date


@st.cache_data
def load_data(
    start_date: datetime.date,
    end_date: datetime.date,
    category_id: int,
    db_last_modified: float,
) -> pd.DataFrame:
    # NOTE: db_last_modified is only used to invalidate the memoized data
    print(f"DB last modified at: {db_last_modified}")
    engine = get_db_engine()
    category_clause = (
        "AND e.category_id=:category"
        if category_id not in {NO_CATEGORY, ALL_CATEGORY}
        else ("AND e.category_id IS NULL" if category_id == NO_CATEGORY else "")
    )
    base_sql = """
    SELECT e.*, JSON_GROUP_ARRAY(et.tag_id) AS tags
    FROM expense e
    LEFT JOIN expense_tag et ON e.id = et.expense_id
    """
    filter_sql = f"""WHERE e.date >= :start_date AND e.date < :end_date
    AND (e.parent IS NULL OR e.parent = '')
    {category_clause}
    GROUP BY e.id;
    """
    params = {"start_date": start_date, "end_date": end_date, "category": category_id}
    if category_id in {NO_CATEGORY, ALL_CATEGORY}:
        params.pop("category")
    sql = text(f"{base_sql} {filter_sql}").bindparams(**params)
    dtype = {"ignore": "bool", "category_id": "Int64", "reviewed": "bool"}
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
def get_categories() -> dict[int, Category]:
    session = get_sqlalchemy_session()
    categories = session.query(Category).order_by("id").all()
    return {cast(int, cat.id): cat for cat in categories}


@st.cache_data
def get_tags() -> dict[int, Tag]:
    session = get_sqlalchemy_session()
    tags = session.query(Tag).order_by("id").all()
    return {cast(int, tag.id): tag for tag in tags}


@st.cache_data
def get_months() -> list[tuple[int, int]]:
    engine = get_db_engine()
    sql = "SELECT date FROM expense"
    data = pd.read_sql_query(sql, engine, parse_dates=["date"])
    months = set(data["date"].apply(lambda x: (x.year, x.month)))
    # NOTE: We use month 13 to represent the whole year
    years = {(y, 13) for (y, _) in months}
    months_sorted = sorted(months.union(years), reverse=True)
    # NOTE: We use (0, 13) to represent All. We need explicit numbers to
    # indicate selection, since we want to select the (current_year,
    # current_month) when year and month are (None, None).
    return [(0, 13), *months_sorted]


def mark_expenses_as_reviewed(expense_ids: list[int]) -> None:
    session = get_sqlalchemy_session()
    expenses = session.query(Expense)
    if expense_ids:
        expenses = expenses.filter(Expense.id.in_(expense_ids))
    expenses.update({"reviewed": True}, synchronize_session=False)
    session.commit()
    st.rerun()


def format_category(category_id: int, categories: dict[int, Category]) -> str:
    if category_id == NO_CATEGORY:
        return "Uncategorized"
    elif category_id == ALL_CATEGORY:
        return "All"
    return str(categories[category_id].name)


def format_tag(tag_id: int, tags: dict[int, Tag]) -> str:
    if tag_id == NO_TAG:
        return "Untagged"
    elif tag_id == ALL_TAG:
        return "All"
    return str(tags[tag_id].name)


def write_changes_to_db(df: pd.DataFrame) -> None:
    # Find the changes
    changes = st.session_state["expenses_data"]["edited_rows"]

    for idx, change in changes.items():
        row = df.iloc[idx]
        # Fetch the expense from the DB
        session = get_sqlalchemy_session()
        expense = session.get(Expense, {"id": row["id"]})
        if expense is None:
            continue

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
def display_summary_stats(data: pd.DataFrame, prev_data: pd.DataFrame) -> None:
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


def display_transactions(
    data: pd.DataFrame, categories: dict[int, Category], tags: dict[int, Tag]
) -> None:
    data_clean = remove_ignored_rows(data)
    m = len(data[data.category_id == NO_CATEGORY])

    n = len(data)
    nc = len(data_clean)
    page_size = 100
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
        show_only_uncategorized = knob1.checkbox(label="Show Only Uncategorized")
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
        df = df if not show_only_unreviewed else cast(pd.DataFrame, df[df.reviewed is False])
        df = df if not show_only_uncategorized else df[df.category_id == NO_CATEGORY]
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
        child_df.index = pd.Index(
            child_df.apply(lambda row: ids.index(row["parent"]) + 0.1, axis=1)
        )
        if not child_df.empty:
            page_df = pd.concat([page_df, child_df]).sort_index(axis=0)

        # Transform the data for display
        page_df["category_id"] = page_df["category_id"].apply(
            lambda x: format_category(x, categories)
        )
        # FIXME: Just use the first tag until we switch to ListColumn
        all_tags = get_tags()
        page_df["tags"] = page_df["tags"].apply(
            lambda tags: str(all_tags[tags[0]].name) if tags else ""
        )
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
                    "Date", format="DD MMM 'YY (ddd)", help="Date of the transaction."
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
                    options=[str(cat.name) for cat in categories.values()],
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
                    options=[str(tag.name) for tag in tags.values()],
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

        _, r4, r3, r2, r1 = st.columns([2, 1, 1, 1, 1])
        mark_page_reviewed = r1.button(
            "Mark Page Reviewed",
            key="mark-page-reviewed",
            help="Mark all transactions in the current page as reviewed",
            disabled=show_all,
        )
        if mark_page_reviewed:
            ids = list(page_df.id)
            mark_expenses_as_reviewed(ids)

        mark_filter_reviewed = r2.button(
            "Mark Filtered Reviewed",
            key="mark-filtered-reviewed",
            help="Mark all transactions in the currently filtered view as reviewed",
        )
        if mark_filter_reviewed:
            ids = list(df.id)
            mark_expenses_as_reviewed(ids)

        mark_all_reviewed = r3.button(
            "Mark *All* Reviewed",
            key="mark-all-reviewed",
            help="Mark all transactions in the DB as reviewed",
        )
        if mark_all_reviewed:
            mark_expenses_as_reviewed([])

        gform_id = os.environ.get("GFORM_ID")
        if gform_id:
            url = f"https://docs.google.com/forms/d/{gform_id}/edit"
            r4.link_button(
                "Add Manual Transaction",
                url,
                help="Open the form to add a manual transaction",
            )


def format_amount(amount: float) -> str:
    amount_label = (
        "-∞"
        if np.isneginf(amount)
        else "∞" if np.isposinf(amount) else f"{CURRENCY_SYMBOL} {amount}"
    )
    return amount_label


def display_extra_filters(
    data: pd.DataFrame, tags: dict[int, Tag], disabled: bool
) -> tuple[Any, Any, Any]:
    counterparties = ["All", *sorted(set(data["counterparty_name"]) - {""})]
    tag_ids = sorted({tag for tags in data.tags for tag in tags})
    options = (-np.inf, 0, 1000, 5000, 10000, 20000, np.inf)
    with st.sidebar:
        counterparty = st.selectbox(
            "Counter Party", counterparties, disabled=disabled, key="cp-filter"
        )
        selected_tags = st.multiselect(
            label="Tags",
            options=tag_ids,
            default=[],
            key="tag-filter",
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


def display_sidebar(
    title: str, categories: dict[int, Category], disabled: bool
) -> tuple[datetime.date, datetime.date, int, int]:
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
        q_year = st.query_params.get("y", None)
        q_month = st.query_params.get("m", None)
        if q_year is not None:
            selection = (int(q_year), int(q_month) if q_month is not None else 13)
            index = months.index(selection)
        else:
            index = min(2, len(months) - 1)
        option = st.selectbox(
            "Time Period",
            months,
            format_func=format_month,
            index=index,
            disabled=disabled,
        )
        st.query_params.y, st.query_params.m = map(str, option)
        start_date, end_date, num_days = daterange_from_year_month(*option)

        category_ids = [ALL_CATEGORY, NO_CATEGORY, *sorted(categories.keys())]
        category = st.selectbox(
            "Category",
            category_ids,
            format_func=lambda x: format_category(x, categories),
            disabled=disabled,
        )

    return start_date, end_date, num_days, category


def remove_ignored_rows(data: pd.DataFrame) -> pd.DataFrame:
    return data[~data["ignore"]].reset_index(drop=True)


def display_barcharts(
    data: pd.DataFrame, categories: dict[int, Category], tags: dict[int, Tag], num_month_days: int
) -> None:
    # Filter ignored transactions
    data = remove_ignored_rows(data)

    if len(data) == 0:
        return

    # Add additional columns for day, category and tags
    data[["day", "category", "tag_names"]] = data.apply(
        lambda row: (
            row["date"].day,
            format_category(row["category_id"], categories),
            [format_tag(tag_id, tags) for tag_id in row["tags"]],
        ),
        axis=1,
        result_type="expand",
    )

    color_scheme = alt.Color("category:N", title="Category")
    click = alt.selection_point(encodings=["color"])

    # Spending by day chart
    chart_day = (
        alt.Chart(data)
        .mark_bar()
        .encode(
            x=alt.X(
                "day:O",
                title="Day of Month",
                scale=alt.Scale(domain=list(range(1, num_month_days + 1))),
            ),
            y=alt.Y("amount:Q", title="Amount"),
            color=alt.condition(
                click,
                if_true=color_scheme,
                if_false=alt.value("lightgray"),
            ),
            tooltip=["category", "amount", "counterparty_name", "remarks"],
        )
        .properties(title="Spending by Day")
        .add_params(click)
    )

    n_cat = len(data.category.unique())
    n_tag = len(data.tag_names.explode().unique())

    if n_cat > 1:
        # Spending by Category chart
        chart_cat = (
            alt.Chart(data)
            .mark_bar()
            .encode(
                y=alt.Y("category:N", title="Category", sort="-x"),
                x=alt.X("amount:Q", title="Amount"),
                color=alt.condition(
                    click,
                    if_true=color_scheme,
                    if_false=alt.value("lightgray"),
                ),
                tooltip=["category", "amount", "remarks"],
            )
            .properties(title="Spending by Category")
            .add_params(click)
        )
    else:
        chart_cat = None

    if n_tag > 1:
        # Spending by Tag chart
        exploded_data = data.explode("tag_names")
        chart_tag = (
            alt.Chart(exploded_data)
            .mark_bar()
            .encode(
                y=alt.Y("tag_names:N", title="Tags", sort="-y"),
                x=alt.X("amount:Q", title="Amount"),
                color=alt.condition(
                    click,
                    if_true=color_scheme,
                    if_false=alt.value("lightgray"),
                ),
                tooltip=["tag_names", "amount", "category", "remarks"],
            )
            .properties(title="Spending by Tag")
            .add_params(click)
        )
    else:
        chart_tag = None

    charts = filter(None, [chart_day, chart_cat, chart_tag])
    # FIXME: Ideally, we'd like (chart_day & (chart_cat | chart_tag)), but it
    # doesn't seem to render due to a bug in altair/streamlit?
    chart = alt.vconcat(*charts)
    st.altair_chart(cast(alt.Chart, chart), use_container_width=True)


def format_row(row: dict[str, Any]) -> str:
    return f"{row['date']:%Y-%m-%d} — {row['amount']:.2f} — {row['details']}:::{row['id']}"


def dashboard() -> None:
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
        col1, col2 = st.columns([4, 1])
        col1.warning("- You have uncommitted changes in your data repository.")
        clicked = col2.button(
            "Manage Repository",
            use_container_width=True,
        )
        if clicked:
            st.switch_page("pages/data_management.py")

    # Sync DB with dump in git DATA repo
    sync_db_with_data_repo()

    # db_last_modified is used to detect DB changes and invalidate Streamlit
    # memoized data
    db_last_modified = os.path.getmtime(DB_PATH)

    categories = get_categories()
    tags = get_tags()
    start_date, end_date, num_month_days, category = display_sidebar(
        title, categories, disabled=False
    )
    data = load_data(start_date, end_date, category, db_last_modified)

    prev_start, prev_end = previous_month(start_date)
    prev_data = load_data(prev_start, prev_end, category, db_last_modified)
    counterparty, selected_tags, (low, high) = display_extra_filters(data, tags, disabled=False)

    if counterparty != "All":
        data = data[data["counterparty_name"] == counterparty]
        prev_data = prev_data[prev_data["counterparty_name"] == counterparty]

    if selected_tags:

        def tag_filter(x: list[str]) -> bool:
            return bool(set(x).intersection(selected_tags))

        data = data[data.tags.apply(tag_filter)]
        prev_data = prev_data[prev_data.tags.apply(tag_filter)]

    def amount_filter_low(data: pd.DataFrame, low: float) -> pd.DataFrame:
        return data[(data.amount >= low) | (data.parent.str.len() > 0)]

    def amount_filter_high(data: pd.DataFrame, high: float) -> pd.DataFrame:
        return data[(data.amount <= high) | (data.parent.str.len() > 0)]

    if not np.isneginf(low):
        data = amount_filter_low(data, low)
        prev_data = amount_filter_low(prev_data, low)

    if not np.isposinf(high):
        data = amount_filter_high(data, high)
        prev_data = amount_filter_high(prev_data, high)

    display_summary_stats(data, prev_data)
    display_barcharts(data, categories, tags, num_month_days)
    display_transactions(data, categories, tags)


dashboard()
