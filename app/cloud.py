import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SAMPLE = ROOT.joinpath("sample")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SAMPLE))

from alembic.config import main as alembic_main
from app.app import main
from app.db_util import DB_PATH, ensure_categories_created, ensure_tags_created
from app.lib.git_manager import GitManager
from app.parse_util import parse_data
from app.util import DATA_REPO_PATH


def prepare_on_cloud():
    if DB_PATH.exists():
        return

    alembic_main(["upgrade", "head"])
    ensure_categories_created()
    ensure_tags_created()
    files = SAMPLE.glob("*.csv")
    GitManager.create_new_repo(DATA_REPO_PATH)

    for path in files:
        csv_type = path.stem.split("-statement", 1)[0]
        parse_data(path, csv_type)


if __name__ == "__main__":
    prepare_on_cloud()
    main()
