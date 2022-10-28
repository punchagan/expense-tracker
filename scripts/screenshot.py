#!/usr/bin/env python
import os
from pathlib import Path
import random
import subprocess
import time

import pytest


THIS = Path(__file__)
HERE = THIS.parent
ROOT = HERE.parent
DB_NAME = "sample-expenses.db"


def test_capture_screenshot(sb):
    screenshot_dir = ROOT.joinpath("screenshots").absolute()
    os.makedirs(screenshot_dir, exist_ok=True)

    sb.open(f"http://localhost:{sb.data}/")
    time.sleep(2)
    path = screenshot_dir.joinpath("latest.png")
    sb.save_screenshot(str(path))

    sb.click(".streamlit-expander .row-widget button")
    time.sleep(2)
    path = screenshot_dir.joinpath("info.png")
    sb.save_screenshot(str(path))


def main(commit=False, use_existing_db=False):
    port = str(random.randint(10000, 20000))

    db_path = ROOT.joinpath(DB_NAME)
    if db_path.exists() and not use_existing_db:
        db_path.unlink()

    subprocess.check_call(["bash", HERE.joinpath("run-sample.sh"), "--no-server"])
    env = os.environ.copy()
    env["EXPENSES_DB"] = DB_NAME
    p = subprocess.Popen(
        [
            "streamlit",
            "run",
            "app/app.py",
            "--theme.base",
            "light",
            "--server.port",
            port,
            "--server.headless",
            "true",
        ],
        cwd=ROOT,
        env=env,
    )
    time.sleep(3)
    pytest.main(
        [
            str(THIS),
            "--browser",
            "firefox",
            "--data",
            port,
            "--window-size",
            "1920,1080",
        ]
    )
    p.kill()

    if commit:
        subprocess.check_call(["git", "add", ROOT.joinpath("screenshots")])
        try:
            subprocess.check_output(
                ["git", "commit", "-m", "screenshot: Update screenshots"]
            )
        except subprocess.CalledProcessError as e:
            print(e.output.decode("utf8").strip().splitlines()[-1])


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c",
        "--commit",
        help="Commit changes to screenshots.",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "-u",
        "--use-existing-db",
        help="Use existing DB.",
        default=False,
        action="store_true",
    )
    args = parser.parse_args()
    main(args.commit, args.use_existing_db)
