#!/usr/bin/env python3

import streamlit as st

from app.components.git_status import setup_repo, check_git_status
from app.lib.git_manager import get_repo_path, GitManager


@st.dialog("Commit Changes to the Data Repository")
def commit_dialog(git_manager: GitManager):
    message = st.text_input("Enter commit message", max_chars=80)
    if st.button("Commit"):
        git_manager.commit_changes(message)
        st.session_state.commit = True
        st.rerun()


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

        if git_manager.is_dirty():
            changes = git_manager.get_uncommitted_changes()
            with st.expander("Repository changes ...", expanded=len(changes) <= 50):
                md = f"```git\n{'\n'.join(changes)}\n```"
                st.markdown(md)
            if st.button("Commit Changes"):
                commit_dialog(git_manager)
        elif st.session_state.get("commit", False):
            st.success("Changes committed successfully!")
            st.balloons()
            del st.session_state.commit
        else:
            st.success("No changes to commit.")

        if st.button("View Dashboard"):
            st.switch_page("pages/dashboard.py")


main()
