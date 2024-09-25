from pathlib import Path

import git

from app.util import DATA_REPO_PATH


class GitManager:
    def __init__(self, repo_path=None):
        if repo_path is None:
            repo_path = DATA_REPO_PATH
        self.repo_path = Path(repo_path)
        self.repo = None
        self._initialize_repo()

    def _initialize_repo(self):
        if self.repo_path.exists():
            try:
                self.repo = git.Repo(self.repo_path)
            except git.exc.InvalidGitRepositoryError as err:
                raise ValueError(
                    f"The directory {self.repo_path} exists but is not a valid git repository."
                ) from err
        else:
            raise FileNotFoundError(f"Repository not found at {self.repo_path}")

    @classmethod
    def create_new_repo(cls, repo_path):
        git.Repo.init(repo_path)
        return cls(repo_path)

    @classmethod
    def clone_repo(cls, clone_url, repo_path):
        git.Repo.clone_from(clone_url, repo_path)
        return cls(repo_path)

    def find_files(self, prefix, suffix):
        return sorted(self.repo_path.glob(f"**/{prefix}-*.{suffix}"))

    def find_latest_file(self, prefix):
        files = self.repo_path.glob(f"**/{prefix}-*")
        # The files have a format of prefix-YYYY-MM
        return max(files)

    def copy_file_to_repo(self, src, prefix, year, month):
        new_name = src.with_stem(f"{prefix}-{year}-{month:02}").name
        repo_sub_path = Path(str(year), new_name)
        return self.copy_file_to_repo_dst(src, repo_sub_path)

    def copy_file_to_repo_dst(self, src, dst):
        new_path = self.repo_path.joinpath(dst)
        new_path.parent.mkdir(parents=True, exist_ok=True)
        src.rename(new_path)
        print(f"Copied {src} to {new_path}")
        return new_path

    def symlink_to_repo_file(self, path, dst):
        src = self.repo_path.joinpath(path)
        if not src.exists():
            raise FileNotFoundError(f"File not found at {src}")

        if dst.is_symlink():
            dst.unlink()

        if dst.exists():
            raise FileExistsError(f"File already exists at {dst}")

        dst.symlink_to(src)
        return dst

    def status(self):
        if not self.repo:
            raise ValueError("Repository not initialized")
        return self.repo.git.status(porcelain="v1").splitlines()

    def get_uncommitted_changes(self):
        if not self.repo:
            raise ValueError("Repository not initialized")
        return self.repo.git.diff(self.repo.head, no_color=True).splitlines()

    def is_dirty(self):
        return bool(self.status())

    def commit_changes(self, message):
        if not self.repo:
            raise ValueError("Repository not initialized")
        self.repo.git.add(A=True)
        self.repo.index.commit(message)
        return f"Committed changes with message: {message}"

    def push_changes(self):
        if not self.repo:
            raise ValueError("Repository not initialized")
        try:
            origin = self.repo.remote("origin")
        except ValueError as err:
            raise ValueError(
                "No remote named 'origin' found. Please set up a remote before pushing."
            ) from err
        origin.push()
        return "Pushed changes to remote repository"
