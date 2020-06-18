import pytest

from random import choice


def pytest_addoption(parser):
    parser.addoption(
        "--pipeline", action="store", default='default',
        help="pipeline config file"
    )
    parser.addoption(
        "--participant_ndx", action="store", default=choice(range(20)),
        help="number from 0 to 19, inclusive"
    )


@pytest.fixture
def pipeline(request):
    return request.config.getoption("--pipeline")


@pytest.fixture
def participant_ndx(request):
    return request.config.getoption("--participant_ndx")