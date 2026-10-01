"""Shared test fixtures."""
import pytest


@pytest.fixture(autouse=True)
def _reset_provisioned():
    """Org names repeat across tests with fresh tmp_paths — clear the SDK's
    once-per-org provisioning cache (the app data the tool reads lives there)."""
    from cycls._agent import state
    state._provisioned.clear()


# Tests marked @pytest.mark.live call the deployed Blender engine. Off by default;
# opt in with `pytest --live` (and CYCLS_API_KEY in the env).

def pytest_addoption(parser):
    parser.addoption("--live", action="store_true", default=False,
                     help="run live tests against the deployed engine")


def pytest_configure(config):
    config.addinivalue_line("markers", "live: calls the deployed engine (opt in with --live)")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--live"):
        return
    skip = pytest.mark.skip(reason="live test (run with --live)")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)
