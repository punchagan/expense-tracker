#!/usr/bin/env python3

import streamlit as st

from app.components.git_status import setup_repo, check_git_status
from app.lib.git_manager import get_repo_path, GitManager


def main():
    st.title("Data Git Repository Management")

    repo_exists = check_git_status()
    if not repo_exists:
        with st.expander(
            "Data git repository not found!", expanded=True, icon=":material/warning:"
        ):
            repo_path = get_repo_path()
            setup_repo(repo_path)

    else:
        git_manager = GitManager()
        st.write(f"Using data repository at `{git_manager.repo_path}`")
        if st.button("View Dashboard"):
            st.switch_page("pages/dashboard.py")


main()
