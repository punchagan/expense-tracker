#!/usr/bin/env python
import os
from pathlib import Path
import sys
import webbrowser

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pyperclip

from app.db_util import get_config_categories

SAMPLE_ID = "1elqWT1w1Asyhf5rixbwIaGb7brk-thYDUOCr5LHHZFI"


def main(sample=False):
    categories = "\n".join(sorted(get_config_categories()))
    pyperclip.copy(categories)
    print("Copied categories to the clipboard")
    gform_id = SAMPLE_ID if sample else os.environ["GFORM_ID"]
    url = f"https://docs.google.com/forms/d/{gform_id}/edit"
    webbrowser.open(url)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--sample", default=False, action="store_true")
    args = parser.parse_args()
    main(args.sample)
