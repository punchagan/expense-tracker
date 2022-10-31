import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from alembic.config import main as alembic_main

from app.app import main
from app.db_util import DB_PATH, ensure_categories_created, ensure_tags_created
from app.parse_util import parse_data


def prepare_on_cloud():
    if DB_PATH.exists():
        return
    alembic_main(["upgrade", "head"])
    ensure_categories_created()
    ensure_tags_created()
    sample_dir = ROOT.joinpath("sample")
    files = sample_dir.glob("*.csv")

    for path in files:
        csv_type = path.stem.split("-statement", 1)[0]
        parse_data(path, csv_type)


if __name__ == "__main__":
    prepare_on_cloud()
    main()
