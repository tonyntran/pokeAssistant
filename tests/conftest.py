import sqlite3

import pytest

from pokeassistant.db import init_db


@pytest.fixture
def mem_db():
    """In-memory SQLite database with schema initialized."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    yield conn
    conn.close()
