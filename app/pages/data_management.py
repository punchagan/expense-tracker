import streamlit as st

from app.components.git_status import check_git_status, setup_repo
from app.lib.git_manager import GitManager
from app.util import DATA_REPO_PATH

NUM_CHANGED_LINES = 50


@st.dialog("Commit Changes to the Data Repository")
def commit_dialog(git_manager: GitManager) -> None:
    message = st.text_input("Enter commit message", max_chars=80)
    if st.button("Commit"):
        git_manager.commit_changes(message)
        st.session_state.commit = True
        st.rerun()


def main() -> None:
    st.title("Data Git Repository Management")

    repo_exists = check_git_status()
    if not repo_exists:
        with st.expander(
            "Data git repository not found!", expanded=True, icon=":material/warning:"
        ):
            setup_repo(DATA_REPO_PATH)

    else:
        git_manager = GitManager()
        st.write(f"Using data repository at `{git_manager.repo_path}`")

        if git_manager.is_dirty():
            status = git_manager.status()
            st.markdown(f"```git\n{'\n'.join(status)}\n```")
            changes = git_manager.get_uncommitted_changes()
            with st.expander("Repository changes ...", expanded=len(changes) <= NUM_CHANGED_LINES):
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
