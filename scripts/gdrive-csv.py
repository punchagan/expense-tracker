#!/usr/bin/env python

import os
import sys
from pathlib import Path

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from app.util import ROOT


def download_sheet():
    downloads = ROOT.joinpath("downloaded_files")
    os.makedirs(downloads, exist_ok=True)
    sheet_id = os.environ["GSHEET_ID"]
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    response = requests.get(url)
    csv_path = downloads.joinpath(f"{sheet_id}.csv")
    with open(csv_path, "w") as f:
        f.write(response.text)


if __name__ == "__main__":
    download_sheet()
