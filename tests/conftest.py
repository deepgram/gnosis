import pytest
from litestar import Litestar
from litestar.testing import TestClient
from app.main import create_app


def pytest_addoption(parser):
    """Adds --update-snapshots flag to pytest."""
    parser.addoption(
        "--update-snapshots",
        action="store_true",
        default=False,
        help="Update snapshots.",
    )


@pytest.fixture(scope="session")
def snapshot_update(request):
    """Fixture to get the value of the --update-snapshots flag."""
    return request.config.getoption("--update-snapshots")


@pytest.fixture(scope="session")
def app() -> Litestar:
    """Fixture to create the Litestar app."""
    return create_app()


@pytest.fixture()
def client(app: Litestar) -> TestClient:
    """Fixture to create a TestClient for the app."""
    return TestClient(app)
