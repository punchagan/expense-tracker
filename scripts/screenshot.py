#!/usr/bin/env python
import os
import random
import subprocess
import time
from pathlib import Path

import pytest

THIS = Path(__file__)
HERE = THIS.parent
ROOT = HERE.parent


def test_capture_screenshot(sb):
    screenshot_dir = ROOT.joinpath("screenshots").absolute()
    os.makedirs(screenshot_dir, exist_ok=True)

    sb.open(f"http://localhost:{sb.data}/")
    time.sleep(2)
    path = screenshot_dir.joinpath("latest.png")
    sb.save_screenshot(str(path))


def set_env_vars(env, script_path):
    """Set env vars from run-sample.sh in our subprocess environment variables."""
    with open(script_path) as f:
        exports = [line for line in f.read().splitlines() if line.startswith("export")]
        for export in exports:
            var, val = export.split(" ")[-1].split("=")
            env[var] = val.strip('"').strip("'")


def main(commit=False, use_existing_db=False):
    port = str(random.randint(10000, 20000))
    sample_script = HERE.joinpath("run-sample.sh")
    env = os.environ.copy()
    set_env_vars(env, sample_script)
    db_name = env["EXPENSES_DB"]
    db_path = ROOT.joinpath(db_name)
    if db_path.exists() and not use_existing_db:
        db_path.unlink()
    subprocess.check_call(["bash", sample_script, "--no-server"], env=env)  # noqa: S603
    p = subprocess.Popen(  # noqa: S603
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
        subprocess.check_call(["git", "add", ROOT.joinpath("screenshots")])  # noqa: S603
        try:
            subprocess.check_output(  # noqa: S603
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
