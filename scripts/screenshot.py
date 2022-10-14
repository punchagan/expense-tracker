#!/usr/bin/env python
import os
from pathlib import Path
import random
import subprocess
import time

import pytest


THIS = Path(__file__)
HERE = THIS.parent
ROOT = THIS.parent.parent


def test_capture_screenshot(sb):
    sb.open(f"http://localhost:{sb.data}/")
    time.sleep(2)
    path = str(
        Path(__file__).parent.parent.joinpath("latest-screenshot.png").absolute()
    )
    sb.save_screenshot(path)


def main():
    port = str(random.randint(10000, 20000))
    subprocess.check_call(["bash", HERE.joinpath("run-sample.sh"), "--no-server"])
    env = os.environ.copy()
    env["EXPENSES_DB"] = "sample-expenses.db"
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
    pytest.main([str(THIS), "--firefox", "--data", port, "--window-size", "1920,1080"])
    p.kill()


if __name__ == "__main__":
    main()
