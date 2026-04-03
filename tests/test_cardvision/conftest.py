import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: mark test as requiring model downloads (skip in CI with -m 'not integration')"
    )
