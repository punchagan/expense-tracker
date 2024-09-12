#!/usr/bin/env python

import os
import sys
from pathlib import Path

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.scrapers import CashStatement

CashStatement().fetch_data()
