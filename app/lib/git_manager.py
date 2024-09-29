from pathlib import Path

import git

from app.util import DATA_REPO_PATH


class GitManager:
    def __init__(self, repo_path: Path | None = None) -> None:
        if repo_path is None:
            repo_path = DATA_REPO_PATH
        self.repo_path = Path(repo_path)
        self.repo = None  # type: git.Repo | None
        self._initialize_repo()

    def _initialize_repo(self) -> None:
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
    def create_new_repo(cls, repo_path: Path) -> "GitManager":
        git.Repo.init(repo_path)
        return cls(repo_path)

    @classmethod
    def clone_repo(cls, clone_url: str, repo_path: Path) -> "GitManager":
        git.Repo.clone_from(clone_url, repo_path)
        return cls(repo_path)

    def find_files(self, prefix: str, suffix: str) -> list[Path]:
        return sorted(self.repo_path.glob(f"**/{prefix}-*.{suffix}"))

    def find_latest_file(self, prefix: str) -> Path:
        files = self.repo_path.glob(f"**/{prefix}-*")
        # The files have a format of prefix-YYYY-MM
        return max(files)

    def copy_file_to_repo(self, src: Path, prefix: str, year: int, month: int) -> Path:
        new_name = src.with_stem(f"{prefix}-{year}-{month:02}").name
        repo_sub_path = Path(str(year), new_name)
        return self.copy_file_to_repo_dst(src, repo_sub_path)

    def copy_file_to_repo_dst(self, src: Path, dst: Path) -> Path:
        new_path = self.repo_path.joinpath(dst)
        new_path.parent.mkdir(parents=True, exist_ok=True)
        src.rename(new_path)
        print(f"Copied {src} to {new_path}")
        return new_path

    def status(self) -> list[str]:
        if not self.repo:
            raise ValueError("Repository not initialized")
        return self.repo.git.status(porcelain="v1").splitlines()

    def get_uncommitted_changes(self) -> list[str]:
        if not self.repo:
            raise ValueError("Repository not initialized")
        return self.repo.git.diff(self.repo.head, no_color=True).splitlines()

    def is_dirty(self) -> bool:
        return bool(self.status())

    def commit_changes(self, message: str) -> str:
        if not self.repo:
            raise ValueError("Repository not initialized")
        self.repo.git.add(A=True)
        self.repo.index.commit(message)
        return f"Committed changes with message: {message}"

    def push_changes(self) -> str:
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
