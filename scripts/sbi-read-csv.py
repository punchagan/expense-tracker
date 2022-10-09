import io
import re
import pandas as pd
from pathlib import Path


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

    with open(from_filename) as f:
        data = f.readlines()
        for idx, line in enumerate(data):
            if "Txn Date" in line:
                n = idx
                break
        else:
            n = 0
    lines = [line.strip().strip(",") for line in data]
    text = "\n".join(lines[n:-2])

    df = pd.read_csv(io.StringIO(text), sep="\t")
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
