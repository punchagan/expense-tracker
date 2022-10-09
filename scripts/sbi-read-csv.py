import io
import pandas as pd
from pathlib import Path
import re
import sys

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.util import extract_csv


def extract_clean_csv(from_filename, to_folderpath):
    """Read a dirty TSV and dump a clean CSV."""
    to_filename = Path(from_filename).with_suffix(".csv").name
    to_path = Path(to_folderpath).absolute().joinpath(to_filename)
    text = extract_csv(from_filename, catch_phrase="Txn Date")
    df = pd.read_csv(text, sep="\t")
    df.columns = [c.strip() for c in df.columns]
    df.to_csv(to_path, index=False)
    return to_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Path to the sbi account statement .xls file")
    parser.add_argument(
        "--to-folder",
        help="Folder path for the to be sbi account statement output .csv file",
        default="sample",
    )

    args = parser.parse_args()

    csv_path = extract_clean_csv(args.path, args.to_folder)
    print(f"Wrote SBI account statement to: {csv_path}")
