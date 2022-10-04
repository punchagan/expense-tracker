import datetime

from pytest import fixture


def pytest_addoption(parser):
    parser.addoption("--start-date", action="store")


@fixture()
def start_date(request):
    start_date = request.config.getoption("--start-date")
    if start_date is None:
        duration = 7
        start_date = datetime.date.today() - datetime.timedelta(duration)
    else:
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()

    return start_date
