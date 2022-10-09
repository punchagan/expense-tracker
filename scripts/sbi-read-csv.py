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
    # Get data from the downloaded folder - "./downloaded_files/sbi-cc-account.xls"
    from_filename = here.joinpath(from_filename)

    with open(from_filename) as f:
        content = f.read()

    content = content.replace(",", "").replace("\t", ",")
    content = re.sub(" +", " ", content)

    to_filename = from_filename.with_suffix(".csv").name
    nfilename = Path(to_folderpath).absolute().joinpath(to_filename)

    with open(nfilename, "w") as f:
        f.write(content)

    df = pd.read_csv(nfilename, sep=",", header=None, names=[0, 1, 2, 3, 4, 5, 6, 7])
    df.fillna(" ", inplace=True)
    df = df[:-1]  # Remove "**This is a computer generate statement..."
    df.to_csv(nfilename, header=False, index=False)
    # Just return the dataframe after it is created - don't
    # because use "sample/sbi-cc-statement.csv" for parsing
    # os.remove(nfilename)
    # return df
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
