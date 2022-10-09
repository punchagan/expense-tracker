import io
import pandas as pd
from pathlib import Path
import re
import sys

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.util import extract_csv


def read_file(from_filename, to_folderpath):
    """
    This function takes the filename of the sbi account statement
    sbi-cc-statement.xls file and returns the path of csv file.
    """
    # Path variables
    here = Path(__file__).parent.parent
    from_filename = here.joinpath(from_filename)
    to_filename = from_filename.with_suffix(".csv").name
    nfilename = Path(to_folderpath).absolute().joinpath(to_filename)
    text = extract_csv(from_filename, catch_phrase="Txn Date")
    df = pd.read_csv(text, sep="\t")
    df.columns = [c.strip() for c in df.columns]
    df.to_csv(nfilename, index=False)
    return nfilename


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

    csv_path = read_file(args.path, args.to_folder)
    print(
        f"Successfully converted the sbi account statement file to csv at: {csv_path}"
    )
