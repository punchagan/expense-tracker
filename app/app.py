# Standard library
import sys
from pathlib import Path

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# 3rd party libs
import streamlit as st


def main():
    nav = st.navigation(
        [
            st.Page(
                "pages/dashboard.py",
                default=True,
                title="Dashboard",
                icon="📊",
            )
        ],
        position="hidden",
    )
    nav.run()


if __name__ == "__main__":
    main()
