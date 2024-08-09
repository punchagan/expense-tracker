from pathlib import Path
import git


class GitManager:
    def __init__(self, repo_path):
        self.repo_path = Path(repo_path)
        self.repo = None
        self._initialize_repo()

    def _initialize_repo(self):
        if self.repo_path.exists():
            try:
                self.repo = git.Repo(self.repo_path)
            except git.exc.InvalidGitRepositoryError:
                raise ValueError(
                    f"The directory {self.repo_path} exists but is not a valid git repository."
                )
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
        except ValueError:
            raise ValueError(
                "No remote named 'origin' found. Please set up a remote before pushing."
            )
        origin.push()
        return "Pushed changes to remote repository"
