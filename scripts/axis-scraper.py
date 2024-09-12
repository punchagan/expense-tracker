import sys
from pathlib import Path

# HACK: include app module in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.scrapers.axis import login, download_account_transactions, download_cc_statement


def test_get_ac_data(sb, start_date, end_date):
    login(sb)
    download_account_transactions(sb, start_date, end_date)


def test_get_cc_data(sb, start_date, end_date):
    login(sb)
    download_cc_statement(sb, start_date, end_date)
