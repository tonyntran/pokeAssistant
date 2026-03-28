"""SQLAlchemy engine and session factory — singleton pattern.

The engine is created once and reused for the process lifetime.
Call reset_engine() to switch databases (e.g., in tests).
"""

from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

from pokeassistant.config import get_db_path
from pokeassistant.models import Base

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def get_engine(db_url: str | None = None) -> Engine:
    """Get or create the singleton SQLAlchemy engine.

    Once created, the engine URL is fixed for the process lifetime.
    Passing a different db_url after first creation is silently ignored.
    To switch databases (e.g., in tests), call reset_engine() first.
    """
    global _engine
    if _engine is None:
        if db_url is None:
            db_url = f"sqlite:///{get_db_path()}"
        echo = os.environ.get("POKEASSISTANT_DEBUG", "").lower() in ("1", "true")
        _engine = create_engine(db_url, echo=echo)
        Base.metadata.create_all(_engine)
    return _engine


def get_session_factory(engine: Engine | None = None) -> sessionmaker:
    """Get or create the singleton session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        if engine is None:
            engine = get_engine()
        _SessionLocal = sessionmaker(bind=engine)
    return _SessionLocal


def reset_engine() -> None:
    """Reset the engine and session factory singletons.

    Required before switching databases (e.g., in tests).
    """
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a session per request, auto-closes after."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()
