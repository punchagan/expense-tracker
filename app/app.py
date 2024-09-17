# Standard library
import sys
from pathlib import Path

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 3rd party libs
import streamlit as st


def main():
    icon = "📊"
    title = "Personal Expense Tracker"
    nav = st.navigation(
        [
            st.Page(
                "pages/dashboard.py",
                default=True,
                title=f"{title} — Dashboard",
                icon=icon,
            ),
            st.Page(
                "pages/data_management.py",
                title=f"{title} — Data Management",
                icon=icon,
            ),
        ],
        position="hidden",
    )
    nav.run()


if __name__ == "__main__":
    main()
