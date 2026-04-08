"""Shared test fixtures and marker registrations."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from pokeassistant.models import Base


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: mark test as requiring model downloads (skip in CI with -m 'not integration')",
    )


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s
