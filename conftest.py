import datetime

from pytest import fixture


def pytest_addoption(parser):
    duration = 7
    start_date = datetime.date.today() - datetime.timedelta(duration)
    default = start_date.strftime("%Y-%m-%d")
    parser.addoption("--start-date", action="store", default=default)


@fixture()
def start_date(request):
    return request.config.getoption("--start-date")
