"""Shared test fixtures."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from pokeassistant.models import Base


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s
