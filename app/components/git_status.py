import sys
from pathlib import Path

import streamlit as st

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.lib.git_manager import GitManager


@st.fragment
def setup_repo(repo_path: Path) -> GitManager | None:
    actions = [
        f"Create a new repository ({repo_path.name})",
        "Clone an existing repository",
    ]
    action = st.radio("Choose an action:", actions)
    git_manager = None

    if action == actions[0]:
        if st.button("Create Repository"):
            try:
                git_manager = GitManager.create_new_repo(repo_path)
                message = f"Initialized new git repository at {repo_path}"
                st.success(message)
            except Exception as e:
                st.error(f"Error creating repository: {e!s}")
    else:
        clone_url = st.text_input("Enter the git clone URL:")
        if st.button("Clone Repository"):
            try:
                git_manager = GitManager.clone_repo(clone_url, repo_path)
                message = f"Cloned repository from {clone_url} to {repo_path}"
                st.success(message)
            except Exception as e:
                st.error(f"Error cloning repository: {e!s}")

    return git_manager


def check_git_status() -> GitManager | None:
    try:
        git_manager = GitManager()
    except (FileNotFoundError, ValueError):
        return None

    return git_manager


if __name__ == "__main__":
    check_git_status()
