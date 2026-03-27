# FastAPI API Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI API layer connecting the React frontend to the SQLite backend, migrating to SQLAlchemy ORM with a repository pattern.

**Architecture:** SQLAlchemy ORM models → abstract repository interface → SQLAlchemy repository implementation → FastAPI endpoints with Pydantic schemas. CLI and scrapers also use the repository. Engine is a module-level singleton.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0+, Pydantic v2, uvicorn, httpx (test), pytest

**Spec:** `docs/superpowers/specs/2026-03-27-fastapi-layer-design.md`

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `pyproject.toml` | Modify | Add fastapi, uvicorn, sqlalchemy, pydantic, httpx deps |
| `src/pokeassistant/models.py` | Rewrite | SQLAlchemy ORM models + dollars_to_cents helper |
| `src/pokeassistant/database.py` | Create | Singleton engine + session factory |
| `src/pokeassistant/schemas.py` | Create | Pydantic response schemas |
| `src/pokeassistant/repository.py` | Create | Abstract repository interface |
| `src/pokeassistant/repositories/__init__.py` | Create | Package init |
| `src/pokeassistant/repositories/sqlalchemy_repo.py` | Create | Concrete SQLAlchemy repository |
| `src/pokeassistant/api.py` | Create | FastAPI app + all endpoints |
| `src/pokeassistant/cli.py` | Modify | Use repository instead of raw db functions |
| `src/pokeassistant/scrapers/tcgcsv.py` | Modify | Use SQLAlchemy model constructors |
| `src/pokeassistant/scrapers/tcgplayer.py` | Modify | Use SQLAlchemy model constructors |
| `src/pokeassistant/scrapers/pricecharting.py` | Modify | Use SQLAlchemy model constructors |
| `src/pokeassistant/scrapers/gemrate.py` | Modify | Use SQLAlchemy model constructors |
| `src/pokeassistant/scrapers/trends.py` | Modify | Use SQLAlchemy model constructors |
| `src/pokeassistant/db.py` | Delete | Replaced by repository |
| `tests/conftest.py` | Rewrite | SQLAlchemy in-memory fixtures |
| `tests/test_models.py` | Rewrite | Test SQLAlchemy models |
| `tests/test_repository.py` | Create | Test all repository methods |
| `tests/test_api.py` | Create | Test all FastAPI endpoints |
| `tests/test_cli.py` | Modify | Mock repository instead of db functions |
| `tests/test_db.py` | Delete | Replaced by test_repository.py |

---

### Task 0: Regression Baseline

**Files:**
- Read: all existing test files

- [ ] **Step 1: Run existing tests and capture baseline**

```bash
cd /home/ttran/projects/pokeAssistant
pip install -e ".[dev]" 2>/dev/null
pytest tests/ -v --tb=short 2>&1 | tee /tmp/baseline-test-output.txt
```

Record how many pass, fail, skip. This is our regression reference.

- [ ] **Step 2: Commit baseline marker**

```bash
git add -A
git commit --allow-empty -m "chore: regression baseline before API layer migration"
```

---

### Task 1: Add Dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add runtime and dev dependencies**

In `pyproject.toml`, replace the `dependencies` and `dev` sections:

```toml
dependencies = [
    "beautifulsoup4>=4.12",
    "playwright>=1.40",
    "pytrends>=4.9",
    "requests>=2.31",
    "pandas>=2.1",
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "sqlalchemy>=2.0",
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-asyncio>=0.23",
    "ruff>=0.1",
    "httpx>=0.27",
]
```

- [ ] **Step 2: Add API script entry**

In `pyproject.toml`, update the `[project.scripts]` section:

```toml
[project.scripts]
pokeassistant = "pokeassistant.cli:main"
pokeassistant-api = "pokeassistant.api:run_server"
```

- [ ] **Step 3: Install updated deps**

```bash
pip install -e ".[dev]"
```

Expected: All new packages install successfully.

- [ ] **Step 4: Verify imports work**

```bash
python -c "import fastapi; import uvicorn; import sqlalchemy; import pydantic; import httpx; print('All imports OK')"
```

Expected: `All imports OK`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml
git commit -m "build: add fastapi, uvicorn, sqlalchemy, pydantic, httpx dependencies"
```

---

### Task 2: Rewrite models.py — SQLAlchemy ORM Models

**Files:**
- Rewrite: `src/pokeassistant/models.py`
- Rewrite: `tests/test_models.py`

- [ ] **Step 1: Write the new test_models.py**

```python
"""Tests for SQLAlchemy ORM models."""

from datetime import datetime, date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from pokeassistant.models import (
    Base,
    Product,
    PriceSnapshot,
    SaleRecord,
    TrendDataPoint,
    GradedPrice,
    PopulationReport,
    dollars_to_cents,
)


@pytest.fixture
def session():
    """In-memory SQLAlchemy session with schema created."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


class TestDollarsToCents:
    def test_whole_dollars(self):
        assert dollars_to_cents(10.0) == 1000

    def test_with_cents(self):
        assert dollars_to_cents(19.99) == 1999

    def test_zero(self):
        assert dollars_to_cents(0.0) == 0

    def test_none_returns_none(self):
        assert dollars_to_cents(None) is None

    def test_negative(self):
        assert dollars_to_cents(-5.50) == -550

    def test_fractional_cent_rounds(self):
        assert dollars_to_cents(10.995) == 1100

    def test_string_float(self):
        assert dollars_to_cents("29.99") == 2999

    def test_string_int(self):
        assert dollars_to_cents("10") == 1000


class TestProduct:
    def test_create_and_persist(self, session):
        p = Product(
            product_id=593355,
            name="Prismatic Evolutions ETB",
            category="Pokemon",
            group_name="Prismatic Evolutions",
            url="https://www.tcgplayer.com/product/593355",
        )
        session.add(p)
        session.flush()
        assert p.product_id == 593355
        assert p.created_at is not None  # default fires on flush

    def test_defaults(self, session):
        p = Product(product_id=1, name="Test")
        session.add(p)
        session.flush()
        assert p.category is None
        assert p.group_name is None
        assert p.url is None
        assert p.image_url is None
        assert p.card_number is None
        assert p.product_type is None
        assert p.rarity is None
        assert p.release_date is None

    def test_new_fields(self, session):
        p = Product(
            product_id=2,
            name="Umbreon ex",
            image_url="https://images.pokemontcg.io/sv8pt5/161_hires.png",
            card_number="161/165",
            product_type="card",
            rarity="Special Illustration Rare",
            release_date=date(2025, 1, 17),
        )
        session.add(p)
        session.flush()
        assert p.image_url == "https://images.pokemontcg.io/sv8pt5/161_hires.png"
        assert p.card_number == "161/165"
        assert p.product_type == "card"
        assert p.release_date == date(2025, 1, 17)

    def test_repr(self):
        p = Product(product_id=1, name="Test", product_type="card")
        assert "Product" in repr(p)
        assert "Test" in repr(p)


class TestPriceSnapshot:
    def test_create(self, session):
        session.add(Product(product_id=1, name="Test"))
        session.flush()
        snap = PriceSnapshot(
            product_id=1,
            timestamp=datetime(2025, 1, 15, 12, 0, 0),
            source="tcgplayer",
            low_price_cents=6499,
            market_price_cents=7250,
            high_price_cents=8999,
            listing_count=42,
        )
        session.add(snap)
        session.flush()
        assert snap.id is not None
        assert snap.low_price_cents == 6499

    def test_optional_fields_default_none(self, session):
        session.add(Product(product_id=1, name="Test"))
        session.flush()
        snap = PriceSnapshot(product_id=1, timestamp=datetime.now(), source="test")
        session.add(snap)
        session.flush()
        assert snap.low_price_cents is None
        assert snap.market_price_cents is None


class TestSaleRecord:
    def test_create(self, session):
        session.add(Product(product_id=1, name="Test"))
        session.flush()
        sale = SaleRecord(
            product_id=1,
            sale_date=date(2025, 1, 15),
            condition="Near Mint",
            variant="Normal",
            price_cents=7500,
            quantity=2,
            source="tcgplayer",
        )
        session.add(sale)
        session.flush()
        assert sale.price_cents == 7500
        assert sale.quantity == 2


class TestTrendDataPoint:
    def test_create(self, session):
        td = TrendDataPoint(
            keyword="prismatic evolutions",
            date=date(2025, 1, 15),
            interest=85,
            source="google_trends",
        )
        session.add(td)
        session.flush()
        assert td.interest == 85


class TestGradedPrice:
    def test_create(self, session):
        session.add(Product(product_id=610516, name="Umbreon ex"))
        session.flush()
        gp = GradedPrice(
            product_id=610516,
            card_name="Umbreon ex #161",
            source="pricecharting",
            timestamp=datetime(2025, 6, 1, 12, 0, 0),
            psa_10_cents=417717,
            grade_9_cents=15000,
        )
        session.add(gp)
        session.flush()
        assert gp.psa_10_cents == 417717
        assert gp.product_id == 610516

    def test_fk_relationship(self, session):
        p = Product(product_id=1, name="Test Card")
        session.add(p)
        session.flush()
        gp = GradedPrice(
            product_id=1, card_name="Test", source="test",
            timestamp=datetime.now(), psa_10_cents=1000,
        )
        session.add(gp)
        session.flush()
        assert gp.product is not None
        assert gp.product.name == "Test Card"


class TestPopulationReport:
    def test_create(self, session):
        pr = PopulationReport(
            card_name="Umbreon ex SIR 161",
            gemrate_id="abc123",
            source="gemrate",
            timestamp=datetime(2025, 6, 1, 12, 0, 0),
            total_population=16344,
            psa_10=5000,
            psa_9=3000,
            gem_rate=30.6,
        )
        session.add(pr)
        session.flush()
        assert pr.total_population == 16344

    def test_fk_relationship(self, session):
        p = Product(product_id=1, name="Test")
        session.add(p)
        session.flush()
        pr = PopulationReport(
            product_id=1, card_name="Test", gemrate_id="x",
            source="test", timestamp=datetime.now(), total_population=100,
        )
        session.add(pr)
        session.flush()
        assert pr.product.name == "Test"
```

- [ ] **Step 2: Run tests — verify they fail (models.py still has dataclasses)**

```bash
pytest tests/test_models.py -v --tb=short 2>&1 | head -30
```

Expected: ImportError or failures because `Base` doesn't exist yet.

- [ ] **Step 3: Write the new models.py**

Replace `src/pokeassistant/models.py` with the full SQLAlchemy ORM models from the spec (Section 2). Include `dollars_to_cents`, `Base`, and all 6 model classes with `DateTime`/`Date` columns, ForeignKeys, relationships (with `order_by` for deterministic ordering), `__repr__`, and `Product.created_at` with `default=datetime.now`.

Complete file content — see spec Section 2 for the exact code. **Important:** All relationships on `Product` must include `order_by` (e.g., `order_by="PriceSnapshot.timestamp"`) to ensure the API's `[-1]` access patterns work on Postgres.

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_models.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pokeassistant/models.py tests/test_models.py
git commit -m "feat: rewrite models.py with SQLAlchemy ORM

- Replace dataclasses with SQLAlchemy declarative models
- Add new columns: image_url, card_number, product_type, rarity, release_date
- Add ForeignKey on GradedPrice.product_id and PopulationReport.product_id
- Add relationships on all models
- Add __repr__ on all models
- Product.created_at has default=datetime.now
- Keep dollars_to_cents helper"
```

---

### Task 3: Create database.py — Engine / Session Factory

**Files:**
- Create: `src/pokeassistant/database.py`
- No separate test file — tested indirectly through test_repository.py and test_api.py

- [ ] **Step 1: Write database.py**

Create `src/pokeassistant/database.py`:

```python
"""SQLAlchemy engine and session factory — singleton pattern.

The engine is created once and reused for the process lifetime.
Call reset_engine() to switch databases (e.g., in tests).
"""

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
```

- [ ] **Step 2: Verify import works**

```bash
python -c "from pokeassistant.database import get_engine, get_db, reset_engine; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/pokeassistant/database.py
git commit -m "feat: add database.py with singleton engine and session factory"
```

---

### Task 4: Create schemas.py — Pydantic Response Schemas

**Files:**
- Create: `src/pokeassistant/schemas.py`

- [ ] **Step 1: Write schemas.py**

Create `src/pokeassistant/schemas.py`:

```python
"""Pydantic response schemas for the FastAPI endpoints."""

from datetime import datetime, date
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class CardSummary(BaseModel):
    id: int
    name: str
    set: str | None = None
    num: str | None = None
    image_url: str | None = None
    market_price_cents: int | None = None
    psa10_price_cents: int | None = None
    psa10_premium_pct: float | None = None
    change_cents: int | None = None
    change_pct: float | None = None


class ConditionPrice(BaseModel):
    condition: str
    price_cents: int


class CardDetail(CardSummary):
    category: str | None = None
    rarity: str | None = None
    url: str | None = None
    condition_prices: list[ConditionPrice] = []
    listing_count: int | None = None


class ProductSummary(BaseModel):
    id: int
    name: str
    set: str | None = None
    image_url: str | None = None
    market_price_cents: int | None = None
    change_cents: int | None = None
    change_pct: float | None = None
    release_date: date | None = None


class ProductDetail(ProductSummary):
    category: str | None = None
    url: str | None = None


class PriceHistoryPoint(BaseModel):
    timestamp: datetime
    market_price_cents: int | None = None
    low_price_cents: int | None = None
    high_price_cents: int | None = None


class GradingRow(BaseModel):
    grade: str
    population: int | None = None
    pct: float | None = None
    price_cents: int | None = None
    trend: str | None = None


class PopulationRow(BaseModel):
    grade: str
    count: int


class TrendPoint(BaseModel):
    date: date
    interest: int
    keyword: str


class SearchResult(BaseModel):
    type: str
    name: str
    sub: str | None = None
    price_cents: int | None = None
    image_url: str | None = None


class HealthResponse(BaseModel):
    status: str
    db: str
```

- [ ] **Step 2: Verify schemas instantiate correctly**

```bash
python -c "
from pokeassistant.schemas import PaginatedResponse, CardSummary, HealthResponse
r = PaginatedResponse[CardSummary](items=[], total=0, limit=50, offset=0)
h = HealthResponse(status='ok', db='connected')
print(r.model_dump_json())
print(h.model_dump_json())
"
```

Expected: Valid JSON output.

- [ ] **Step 3: Commit**

```bash
git add src/pokeassistant/schemas.py
git commit -m "feat: add Pydantic response schemas with generic PaginatedResponse"
```

---

### Task 5: Create repository.py — Abstract Interface

**Files:**
- Create: `src/pokeassistant/repository.py`

- [ ] **Step 1: Write repository.py**

Create `src/pokeassistant/repository.py`:

```python
"""Abstract repository interface for data access.

Implementations: SQLAlchemyRepository (current), SupabaseRepository (future).
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pokeassistant.models import (
        Product, PriceSnapshot, SaleRecord,
        TrendDataPoint, GradedPrice, PopulationReport,
    )


class CardRepository(ABC):

    # --- Read: Cards ---

    @abstractmethod
    def list_cards(
        self,
        limit: int = 50,
        offset: int = 0,
        category: str | None = None,
        search: str | None = None,
        sort_by: str = "market_price",
        order: str = "desc",
    ) -> tuple[list, int]:
        """Return (cards, total_count). Filters on product_type='card'."""
        ...

    @abstractmethod
    def get_card(self, product_id: int):
        """Return a single card by product_id, or None."""
        ...

    @abstractmethod
    def get_price_history(self, product_id: int, period: str = "1M") -> list:
        """Return price snapshots for a product within the given period."""
        ...

    @abstractmethod
    def get_price_change(self, product_id: int) -> tuple[int | None, float | None]:
        """Return (change_cents, change_pct) from the two most recent snapshots."""
        ...

    # --- Read: Products (sealed) ---

    @abstractmethod
    def list_products(
        self,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
        sort_by: str = "market_price",
        order: str = "desc",
    ) -> tuple[list, int]:
        """Return (products, total_count). Filters on product_type='sealed'."""
        ...

    @abstractmethod
    def get_product(self, product_id: int):
        """Return a single sealed product by product_id, or None."""
        ...

    # --- Read: Grading & Population ---

    @abstractmethod
    def get_grading(self, product_id: int) -> list:
        """Return graded price data for a card by product_id."""
        ...

    @abstractmethod
    def get_population(self, product_id: int) -> list:
        """Return population report data for a card by product_id."""
        ...

    # --- Read: Trends ---

    @abstractmethod
    def get_trend_data(self, keyword: str) -> list:
        """Return trend data points for a keyword, ordered by date."""
        ...

    # --- Read: Search ---

    @abstractmethod
    def search(self, query: str, result_type: str | None = None) -> list:
        """Search products by name. Optionally filter by type ('card'/'product')."""
        ...

    # --- Write ---

    @abstractmethod
    def upsert_product(self, product: "Product") -> None:
        """Insert or update a product. See spec for upsert semantics."""
        ...

    @abstractmethod
    def insert_price_snapshot(self, snapshot: "PriceSnapshot") -> None:
        """Insert a price snapshot. Ignore on unique constraint conflict."""
        ...

    @abstractmethod
    def insert_sale_record(self, sale: "SaleRecord") -> None:
        """Insert a sale record. Ignore on unique constraint conflict."""
        ...

    @abstractmethod
    def insert_trend_data(self, trend: "TrendDataPoint") -> None:
        """Insert a trend data point. Ignore on unique constraint conflict."""
        ...

    @abstractmethod
    def insert_graded_price(self, graded: "GradedPrice") -> None:
        """Insert a graded price record. Ignore on unique constraint conflict."""
        ...

    @abstractmethod
    def insert_population_report(self, report: "PopulationReport") -> None:
        """Insert a population report. Ignore on unique constraint conflict."""
        ...
```

- [ ] **Step 2: Verify import**

```bash
python -c "from pokeassistant.repository import CardRepository; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add src/pokeassistant/repository.py
git commit -m "feat: add abstract CardRepository interface"
```

---

### Task 6: Create SQLAlchemy Repository — Write Operations

**Files:**
- Create: `src/pokeassistant/repositories/__init__.py`
- Create: `src/pokeassistant/repositories/sqlalchemy_repo.py`
- Create: `tests/test_repository.py` (write tests first)

- [ ] **Step 1: Create package init**

Create `src/pokeassistant/repositories/__init__.py`:

```python
from pokeassistant.repositories.sqlalchemy_repo import SQLAlchemyRepository

__all__ = ["SQLAlchemyRepository"]
```

- [ ] **Step 2: Write tests for write operations**

Create `tests/test_repository.py`:

```python
"""Tests for SQLAlchemyRepository."""

from datetime import datetime, date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from pokeassistant.models import (
    Base, Product, PriceSnapshot, SaleRecord,
    TrendDataPoint, GradedPrice, PopulationReport,
)
from pokeassistant.repositories.sqlalchemy_repo import SQLAlchemyRepository


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def repo(session):
    return SQLAlchemyRepository(session)


class TestUpsertProduct:
    def test_insert_new(self, repo, session):
        p = Product(product_id=1, name="Test Card", product_type="card")
        repo.upsert_product(p)
        result = session.get(Product, 1)
        assert result is not None
        assert result.name == "Test Card"
        assert result.created_at is not None

    def test_update_name(self, repo, session):
        repo.upsert_product(Product(product_id=1, name="Original"))
        repo.upsert_product(Product(product_id=1, name="Updated"))
        result = session.get(Product, 1)
        assert result.name == "Updated"

    def test_update_preserves_existing_non_null(self, repo, session):
        repo.upsert_product(Product(
            product_id=1, name="Card",
            image_url="https://example.com/img.png",
            product_type="card",
        ))
        # Second scraper doesn't know image_url
        repo.upsert_product(Product(product_id=1, name="Card", category="Pokemon"))
        result = session.get(Product, 1)
        assert result.image_url == "https://example.com/img.png"  # preserved
        assert result.category == "Pokemon"  # updated
        assert result.product_type == "card"  # preserved

    def test_update_overwrites_with_non_null(self, repo, session):
        repo.upsert_product(Product(product_id=1, name="Card", image_url="old.png"))
        repo.upsert_product(Product(product_id=1, name="Card", image_url="new.png"))
        result = session.get(Product, 1)
        assert result.image_url == "new.png"


class TestInsertPriceSnapshot:
    def test_insert(self, repo, session):
        repo.upsert_product(Product(product_id=1, name="Test"))
        snap = PriceSnapshot(
            product_id=1, timestamp=datetime(2025, 1, 15, 12, 0),
            source="tcgplayer", market_price_cents=7250,
        )
        repo.insert_price_snapshot(snap)
        results = session.query(PriceSnapshot).filter_by(product_id=1).all()
        assert len(results) == 1
        assert results[0].market_price_cents == 7250

    def test_dedup_on_unique(self, repo, session):
        repo.upsert_product(Product(product_id=1, name="Test"))
        snap = PriceSnapshot(
            product_id=1, timestamp=datetime(2025, 1, 15, 12, 0),
            source="tcgplayer", market_price_cents=7250,
        )
        repo.insert_price_snapshot(snap)
        # Same timestamp+source — should be ignored
        snap2 = PriceSnapshot(
            product_id=1, timestamp=datetime(2025, 1, 15, 12, 0),
            source="tcgplayer", market_price_cents=9999,
        )
        repo.insert_price_snapshot(snap2)
        results = session.query(PriceSnapshot).filter_by(product_id=1).all()
        assert len(results) == 1

    def test_different_sources_not_deduped(self, repo, session):
        repo.upsert_product(Product(product_id=1, name="Test"))
        ts = datetime(2025, 1, 15, 12, 0)
        repo.insert_price_snapshot(PriceSnapshot(
            product_id=1, timestamp=ts, source="tcgplayer", market_price_cents=7250,
        ))
        repo.insert_price_snapshot(PriceSnapshot(
            product_id=1, timestamp=ts, source="tcgcsv", market_price_cents=7300,
        ))
        results = session.query(PriceSnapshot).filter_by(product_id=1).all()
        assert len(results) == 2


class TestInsertSaleRecord:
    def test_insert(self, repo, session):
        repo.upsert_product(Product(product_id=1, name="Test"))
        sale = SaleRecord(
            product_id=1, sale_date=date(2025, 1, 15),
            condition="NM", variant="Normal",
            price_cents=7500, quantity=2, source="tcgplayer",
        )
        repo.insert_sale_record(sale)
        results = session.query(SaleRecord).filter_by(product_id=1).all()
        assert len(results) == 1

    def test_dedup(self, repo, session):
        repo.upsert_product(Product(product_id=1, name="Test"))
        sale = SaleRecord(
            product_id=1, sale_date=date(2025, 1, 15),
            condition="NM", variant="Normal",
            price_cents=7500, source="tcgplayer",
        )
        repo.insert_sale_record(sale)
        sale2 = SaleRecord(
            product_id=1, sale_date=date(2025, 1, 15),
            condition="NM", variant="Normal",
            price_cents=7500, source="tcgplayer",
        )
        repo.insert_sale_record(sale2)
        assert session.query(SaleRecord).count() == 1


class TestInsertTrendData:
    def test_insert(self, repo, session):
        td = TrendDataPoint(
            keyword="prismatic evolutions", date=date(2025, 1, 15),
            interest=85, source="google_trends",
        )
        repo.insert_trend_data(td)
        results = session.query(TrendDataPoint).all()
        assert len(results) == 1

    def test_dedup(self, repo, session):
        td = TrendDataPoint(
            keyword="test", date=date(2025, 1, 15),
            interest=50, source="google_trends",
        )
        repo.insert_trend_data(td)
        td2 = TrendDataPoint(
            keyword="test", date=date(2025, 1, 15),
            interest=60, source="google_trends",
        )
        repo.insert_trend_data(td2)
        assert session.query(TrendDataPoint).count() == 1


class TestInsertGradedPrice:
    def test_insert(self, repo, session):
        repo.upsert_product(Product(product_id=1, name="Test"))
        gp = GradedPrice(
            product_id=1, card_name="Umbreon ex #161",
            source="pricecharting", timestamp=datetime(2025, 6, 1, 12, 0),
            psa_10_cents=417717,
        )
        repo.insert_graded_price(gp)
        results = session.query(GradedPrice).all()
        assert len(results) == 1
        assert results[0].psa_10_cents == 417717


class TestInsertPopulationReport:
    def test_insert(self, repo, session):
        pr = PopulationReport(
            card_name="Umbreon ex SIR 161", gemrate_id="abc123",
            source="gemrate", timestamp=datetime(2025, 6, 1, 12, 0),
            total_population=16344, psa_10=5000,
        )
        repo.insert_population_report(pr)
        results = session.query(PopulationReport).all()
        assert len(results) == 1
        assert results[0].total_population == 16344
```

- [ ] **Step 3: Run tests — verify they fail**

```bash
pytest tests/test_repository.py -v --tb=short 2>&1 | head -10
```

Expected: ImportError (sqlalchemy_repo.py doesn't exist).

- [ ] **Step 4: Write the repository implementation (write operations)**

Create `src/pokeassistant/repositories/sqlalchemy_repo.py`:

```python
"""SQLAlchemy implementation of CardRepository."""

from datetime import datetime, date, timedelta

from sqlalchemy import func, desc, asc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from pokeassistant.models import (
    Product, PriceSnapshot, SaleRecord,
    TrendDataPoint, GradedPrice, PopulationReport,
)
from pokeassistant.repository import CardRepository

# Fields that use COALESCE-style upsert (only overwrite if incoming is not None)
_UPSERT_COALESCE_FIELDS = (
    "image_url", "card_number", "product_type", "rarity",
    "release_date", "category", "group_name", "url",
)


class SQLAlchemyRepository(CardRepository):

    def __init__(self, session: Session):
        self.session = session

    # --- Write Operations ---

    def upsert_product(self, product: Product) -> None:
        existing = self.session.get(Product, product.product_id)
        if existing:
            existing.name = product.name
            for field in _UPSERT_COALESCE_FIELDS:
                incoming = getattr(product, field)
                if incoming is not None:
                    setattr(existing, field, incoming)
        else:
            self.session.add(product)
        self.session.commit()

    def _insert_ignore(self, obj) -> None:
        """Insert an object, silently ignoring unique constraint violations."""
        try:
            self.session.add(obj)
            self.session.commit()
        except IntegrityError:
            self.session.rollback()

    def insert_price_snapshot(self, snapshot: PriceSnapshot) -> None:
        self._insert_ignore(snapshot)

    def insert_sale_record(self, sale: SaleRecord) -> None:
        self._insert_ignore(sale)

    def insert_trend_data(self, trend: TrendDataPoint) -> None:
        self._insert_ignore(trend)

    def insert_graded_price(self, graded: GradedPrice) -> None:
        self._insert_ignore(graded)

    def insert_population_report(self, report: PopulationReport) -> None:
        self._insert_ignore(report)

    # --- Read Operations (stubs — implemented in Task 7) ---

    def list_cards(self, limit=50, offset=0, category=None, search=None,
                   sort_by="market_price", order="desc"):
        raise NotImplementedError

    def get_card(self, product_id):
        raise NotImplementedError

    def get_price_history(self, product_id, period="1M"):
        raise NotImplementedError

    def get_price_change(self, product_id):
        raise NotImplementedError

    def list_products(self, limit=50, offset=0, search=None,
                      sort_by="market_price", order="desc"):
        raise NotImplementedError

    def get_product(self, product_id):
        raise NotImplementedError

    def get_grading(self, product_id):
        raise NotImplementedError

    def get_population(self, product_id):
        raise NotImplementedError

    def get_trend_data(self, keyword):
        raise NotImplementedError

    def search(self, query, result_type=None):
        raise NotImplementedError
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
pytest tests/test_repository.py -v
```

Expected: All write operation tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/pokeassistant/repositories/ tests/test_repository.py
git commit -m "feat: add SQLAlchemyRepository with write operations

- upsert_product with COALESCE semantics
- insert_ignore for all other write methods
- Read operations stubbed as NotImplementedError"
```

---

### Task 7: Repository Read Operations

**Files:**
- Modify: `src/pokeassistant/repositories/sqlalchemy_repo.py`
- Modify: `tests/test_repository.py`

- [ ] **Step 1: Add read operation tests to test_repository.py**

Append to `tests/test_repository.py`:

```python
class TestListCards:
    def test_returns_only_cards(self, repo, session):
        repo.upsert_product(Product(product_id=1, name="Card", product_type="card"))
        repo.upsert_product(Product(product_id=2, name="ETB", product_type="sealed"))
        cards, total = repo.list_cards()
        assert total == 1
        assert cards[0].product_id == 1

    def test_pagination(self, repo):
        for i in range(5):
            repo.upsert_product(Product(product_id=i+1, name=f"Card {i}", product_type="card"))
        cards, total = repo.list_cards(limit=2, offset=0)
        assert len(cards) == 2
        assert total == 5
        cards2, _ = repo.list_cards(limit=2, offset=2)
        assert len(cards2) == 2

    def test_search_filter(self, repo):
        repo.upsert_product(Product(product_id=1, name="Umbreon ex", product_type="card"))
        repo.upsert_product(Product(product_id=2, name="Pikachu ex", product_type="card"))
        cards, total = repo.list_cards(search="umbreon")
        assert total == 1
        assert cards[0].name == "Umbreon ex"

    def test_sort_by_name(self, repo):
        repo.upsert_product(Product(product_id=1, name="Zebra", product_type="card"))
        repo.upsert_product(Product(product_id=2, name="Alpha", product_type="card"))
        cards, _ = repo.list_cards(sort_by="name", order="asc")
        assert cards[0].name == "Alpha"
        assert cards[1].name == "Zebra"

    def test_empty(self, repo):
        cards, total = repo.list_cards()
        assert cards == []
        assert total == 0


class TestGetCard:
    def test_found(self, repo):
        repo.upsert_product(Product(product_id=1, name="Test", product_type="card"))
        assert repo.get_card(1) is not None

    def test_not_found(self, repo):
        assert repo.get_card(999) is None


class TestListProducts:
    def test_returns_only_sealed(self, repo):
        repo.upsert_product(Product(product_id=1, name="Card", product_type="card"))
        repo.upsert_product(Product(product_id=2, name="ETB", product_type="sealed"))
        prods, total = repo.list_products()
        assert total == 1
        assert prods[0].product_id == 2

    def test_sort_by_release_date(self, repo):
        repo.upsert_product(Product(
            product_id=1, name="Old", product_type="sealed",
            release_date=date(2024, 1, 1),
        ))
        repo.upsert_product(Product(
            product_id=2, name="New", product_type="sealed",
            release_date=date(2025, 6, 1),
        ))
        prods, _ = repo.list_products(sort_by="release_date", order="desc")
        assert prods[0].name == "New"


class TestGetProduct:
    def test_found(self, repo):
        repo.upsert_product(Product(product_id=1, name="ETB", product_type="sealed"))
        assert repo.get_product(1) is not None

    def test_not_found(self, repo):
        assert repo.get_product(999) is None


class TestPriceHistory:
    def test_returns_ordered(self, repo):
        repo.upsert_product(Product(product_id=1, name="Test"))
        repo.insert_price_snapshot(PriceSnapshot(
            product_id=1, timestamp=datetime(2025, 3, 1), source="s", market_price_cents=100,
        ))
        repo.insert_price_snapshot(PriceSnapshot(
            product_id=1, timestamp=datetime(2025, 3, 15), source="s", market_price_cents=200,
        ))
        history = repo.get_price_history(1, period="ALL")
        assert len(history) == 2
        assert history[0].timestamp < history[1].timestamp

    def test_period_filter(self, repo):
        repo.upsert_product(Product(product_id=1, name="Test"))
        repo.insert_price_snapshot(PriceSnapshot(
            product_id=1, timestamp=datetime(2020, 1, 1), source="s", market_price_cents=100,
        ))
        repo.insert_price_snapshot(PriceSnapshot(
            product_id=1, timestamp=datetime.now(), source="s2", market_price_cents=200,
        ))
        history = repo.get_price_history(1, period="1M")
        assert len(history) == 1  # Only the recent one


class TestPriceChange:
    def test_computes_change(self, repo):
        repo.upsert_product(Product(product_id=1, name="Test"))
        repo.insert_price_snapshot(PriceSnapshot(
            product_id=1, timestamp=datetime(2025, 3, 1), source="s", market_price_cents=1000,
        ))
        repo.insert_price_snapshot(PriceSnapshot(
            product_id=1, timestamp=datetime(2025, 3, 15), source="s2", market_price_cents=1200,
        ))
        change_cents, change_pct = repo.get_price_change(1)
        assert change_cents == 200
        assert abs(change_pct - 20.0) < 0.01

    def test_no_snapshots(self, repo):
        repo.upsert_product(Product(product_id=1, name="Test"))
        change_cents, change_pct = repo.get_price_change(1)
        assert change_cents is None
        assert change_pct is None

    def test_single_snapshot(self, repo):
        repo.upsert_product(Product(product_id=1, name="Test"))
        repo.insert_price_snapshot(PriceSnapshot(
            product_id=1, timestamp=datetime(2025, 3, 1), source="s", market_price_cents=1000,
        ))
        change_cents, change_pct = repo.get_price_change(1)
        assert change_cents is None
        assert change_pct is None


class TestGetGrading:
    def test_returns_grading(self, repo):
        repo.upsert_product(Product(product_id=1, name="Test"))
        repo.insert_graded_price(GradedPrice(
            product_id=1, card_name="Test", source="pc",
            timestamp=datetime(2025, 6, 1), psa_10_cents=4000,
        ))
        results = repo.get_grading(1)
        assert len(results) == 1


class TestGetPopulation:
    def test_returns_population(self, repo):
        repo.upsert_product(Product(product_id=1, name="Test"))
        repo.insert_population_report(PopulationReport(
            product_id=1, card_name="Test", gemrate_id="x",
            source="gr", timestamp=datetime(2025, 6, 1), total_population=100,
        ))
        results = repo.get_population(1)
        assert len(results) == 1


class TestGetTrendData:
    def test_returns_ordered(self, repo):
        repo.insert_trend_data(TrendDataPoint(
            keyword="test", date=date(2025, 3, 15), interest=80, source="gt",
        ))
        repo.insert_trend_data(TrendDataPoint(
            keyword="test", date=date(2025, 3, 1), interest=50, source="gt",
        ))
        results = repo.get_trend_data("test")
        assert len(results) == 2
        assert results[0].date < results[1].date

    def test_filters_by_keyword(self, repo):
        repo.insert_trend_data(TrendDataPoint(
            keyword="a", date=date(2025, 3, 1), interest=50, source="gt",
        ))
        repo.insert_trend_data(TrendDataPoint(
            keyword="b", date=date(2025, 3, 1), interest=60, source="gt",
        ))
        results = repo.get_trend_data("a")
        assert len(results) == 1


class TestSearch:
    def test_search_cards(self, repo):
        repo.upsert_product(Product(product_id=1, name="Umbreon ex", product_type="card"))
        repo.upsert_product(Product(product_id=2, name="ETB", product_type="sealed"))
        results = repo.search("umbreon", result_type="card")
        assert len(results) == 1
        assert results[0].name == "Umbreon ex"

    def test_search_all(self, repo):
        repo.upsert_product(Product(product_id=1, name="Umbreon ex", product_type="card"))
        repo.upsert_product(Product(product_id=2, name="Umbreon Box", product_type="sealed"))
        results = repo.search("umbreon")
        assert len(results) == 2

    def test_search_empty(self, repo):
        results = repo.search("nonexistent")
        assert results == []
```

- [ ] **Step 2: Run tests — verify new tests fail**

```bash
pytest tests/test_repository.py::TestListCards -v --tb=short 2>&1 | head -10
```

Expected: NotImplementedError.

- [ ] **Step 3: Implement all read operations in sqlalchemy_repo.py**

Replace the read operation stubs in `sqlalchemy_repo.py` with full implementations. Key logic:

- `list_cards` / `list_products`: Query `Product` filtered by `product_type`, with `LIKE` search on name, pagination via `offset`/`limit`, count via separate `func.count()` query. Sort mapping:
  - `name`: `order_by(Product.name)`
  - `release_date`: `order_by(Product.release_date)`
  - `market_price` (requires subquery for latest snapshot):
    ```python
    from sqlalchemy import select, func
    latest_price = (
        select(PriceSnapshot.market_price_cents)
        .where(PriceSnapshot.product_id == Product.product_id)
        .order_by(PriceSnapshot.timestamp.desc())
        .limit(1)
        .correlate(Product)
        .scalar_subquery()
    )
    query = query.order_by(desc(latest_price))  # or asc()
    ```
  - `change`: Similar subquery approach comparing the last two snapshots — or just order by name as a simpler fallback (change sort is best-effort).
- `get_card` / `get_product`: `session.get(Product, product_id)`.
- `get_price_history`: Filter `PriceSnapshot` by product_id, optionally filter by date range based on period mapping (`1M`=30d, `3M`=90d, `6M`=180d, `1Y`=365d, `ALL`=no filter), order by timestamp ascending.
- `get_price_change`: Get last 2 snapshots ordered by timestamp desc, compute delta.
- `get_grading`: Query `GradedPrice` where `product_id` matches, ordered by timestamp desc.
- `get_population`: Query `PopulationReport` where `product_id` matches, ordered by timestamp desc.
- `get_trend_data`: Query `TrendDataPoint` where `keyword` matches, ordered by date asc.
- `search`: `LIKE '%query%'` on `Product.name`, optionally filter by `product_type` (map `"card"` and `"product"`→`"sealed"`), limit 20.

- [ ] **Step 4: Run all repository tests**

```bash
pytest tests/test_repository.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pokeassistant/repositories/sqlalchemy_repo.py tests/test_repository.py
git commit -m "feat: implement repository read operations

- list_cards/list_products with sort, search, pagination
- get_card/get_product by ID
- get_price_history with period filter
- get_price_change computed from latest 2 snapshots
- get_grading, get_population, get_trend_data
- search with LIKE and type filter"
```

---

### Task 8: Create api.py — FastAPI App + Health + Card Endpoints

**Files:**
- Create: `src/pokeassistant/api.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write API tests**

Create `tests/test_api.py`:

```python
"""Tests for FastAPI endpoints."""

from datetime import datetime, date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from pokeassistant.models import (
    Base, Product, PriceSnapshot, GradedPrice, PopulationReport, TrendDataPoint,
)
from pokeassistant.repositories.sqlalchemy_repo import SQLAlchemyRepository
from pokeassistant.api import app, get_repo


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(session):
    repo = SQLAlchemyRepository(session)

    def override_repo():
        return repo

    def override_db():
        yield session

    app.dependency_overrides[get_repo] = override_repo
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_client(client, session):
    """Client with sample data pre-loaded."""
    repo = SQLAlchemyRepository(session)

    # Cards
    repo.upsert_product(Product(
        product_id=1, name="Umbreon ex", product_type="card",
        group_name="Prismatic Evolutions", card_number="161/165",
        image_url="https://example.com/umbreon.png",
    ))
    repo.upsert_product(Product(
        product_id=2, name="Pikachu ex", product_type="card",
        group_name="Ascended Heroes", card_number="276/217",
    ))

    # Sealed products
    repo.upsert_product(Product(
        product_id=10, name="Booster Bundle", product_type="sealed",
        group_name="Ascended Heroes", release_date=date(2025, 6, 1),
    ))

    # Price snapshots for Umbreon
    repo.insert_price_snapshot(PriceSnapshot(
        product_id=1, timestamp=datetime(2025, 3, 1), source="tcg",
        market_price_cents=120000,
    ))
    repo.insert_price_snapshot(PriceSnapshot(
        product_id=1, timestamp=datetime(2025, 3, 15), source="tcg2",
        market_price_cents=139500,
    ))

    # Graded prices
    repo.insert_graded_price(GradedPrice(
        product_id=1, card_name="Umbreon ex", source="pc",
        timestamp=datetime(2025, 3, 15), psa_10_cents=450000,
    ))

    # Population
    repo.insert_population_report(PopulationReport(
        product_id=1, card_name="Umbreon ex", gemrate_id="abc",
        source="gr", timestamp=datetime(2025, 3, 15),
        total_population=4424, psa_10=1842, psa_9=1204,
    ))

    # Trends
    repo.insert_trend_data(TrendDataPoint(
        keyword="umbreon ex", date=date(2025, 3, 1), interest=85, source="gt",
    ))

    return client


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["db"] == "connected"


class TestListCards:
    def test_returns_cards(self, seeded_client):
        resp = seeded_client.get("/api/cards")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_pagination(self, seeded_client):
        resp = seeded_client.get("/api/cards?limit=1&offset=0")
        data = resp.json()
        assert len(data["items"]) == 1
        assert data["total"] == 2

    def test_search(self, seeded_client):
        resp = seeded_client.get("/api/cards?search=umbreon")
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Umbreon ex"

    def test_empty(self, client):
        resp = client.get("/api/cards")
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_invalid_sort_by(self, client):
        resp = client.get("/api/cards?sort_by=invalid")
        assert resp.status_code == 422


class TestGetCard:
    def test_found(self, seeded_client):
        resp = seeded_client.get("/api/cards/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Umbreon ex"
        assert data["set"] == "Prismatic Evolutions"
        assert data["num"] == "161/165"

    def test_not_found(self, client):
        resp = client.get("/api/cards/999")
        assert resp.status_code == 404


class TestCardPriceHistory:
    def test_returns_history(self, seeded_client):
        resp = seeded_client.get("/api/cards/1/price-history?period=ALL")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2


class TestListProducts:
    def test_returns_sealed(self, seeded_client):
        resp = seeded_client.get("/api/products")
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "Booster Bundle"


class TestGetProduct:
    def test_found(self, seeded_client):
        resp = seeded_client.get("/api/products/10")
        assert resp.status_code == 200

    def test_not_found(self, client):
        resp = client.get("/api/products/999")
        assert resp.status_code == 404


class TestSearch:
    def test_search_all(self, seeded_client):
        resp = seeded_client.get("/api/search?q=umbreon")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    def test_search_empty_query(self, client):
        resp = client.get("/api/search?q=")
        assert resp.status_code == 200


class TestTrends:
    def test_returns_data(self, seeded_client):
        resp = seeded_client.get("/api/trends/umbreon%20ex")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1

    def test_empty_keyword(self, seeded_client):
        resp = seeded_client.get("/api/trends/nonexistent")
        data = resp.json()
        assert data == []


class TestGrading:
    def test_returns_data(self, seeded_client):
        resp = seeded_client.get("/api/grading/1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1


class TestPopulation:
    def test_returns_data(self, seeded_client):
        resp = seeded_client.get("/api/population/1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_api.py -v --tb=short 2>&1 | head -10
```

Expected: ImportError (api.py doesn't exist).

- [ ] **Step 3: Write api.py with all endpoints**

Create `src/pokeassistant/api.py`:

```python
"""FastAPI application with all endpoints."""

from typing import Literal

from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from pokeassistant.database import get_db, get_session_factory
from pokeassistant.repositories.sqlalchemy_repo import SQLAlchemyRepository
from pokeassistant.schemas import (
    HealthResponse, PaginatedResponse, CardSummary, CardDetail,
    ProductSummary, ProductDetail, PriceHistoryPoint,
    GradingRow, PopulationRow, TrendPoint, SearchResult, ConditionPrice,
)

app = FastAPI(title="PokeAssistant API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

VALID_CARD_SORTS = {"market_price", "name", "change"}
VALID_PRODUCT_SORTS = {"market_price", "name", "change", "release_date"}


def get_repo(session: Session = Depends(get_db)) -> SQLAlchemyRepository:
    return SQLAlchemyRepository(session)


# --- Health ---

@app.get("/api/health", response_model=HealthResponse)
def health_check(session: Session = Depends(get_db)):
    try:
        session.execute(text("SELECT 1"))
        return HealthResponse(status="ok", db="connected")
    except Exception:
        return HealthResponse(status="degraded", db="disconnected")


# --- Cards ---

@app.get("/api/cards", response_model=PaginatedResponse[CardSummary])
def list_cards(
    repo: SQLAlchemyRepository = Depends(get_repo),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    category: str | None = None,
    search: str | None = None,
    sort_by: str = "market_price",
    order: str = "desc",
):
    if sort_by not in VALID_CARD_SORTS:
        raise HTTPException(422, f"Invalid sort_by. Valid: {VALID_CARD_SORTS}")
    if order not in ("asc", "desc"):
        raise HTTPException(422, "Invalid order. Valid: asc, desc")

    cards, total = repo.list_cards(
        limit=limit, offset=offset, category=category,
        search=search, sort_by=sort_by, order=order,
    )

    items = []
    for card in cards:
        change_cents, change_pct = repo.get_price_change(card.product_id)
        latest_snap = (card.price_snapshots[-1] if card.price_snapshots else None)
        market = latest_snap.market_price_cents if latest_snap else None

        # PSA 10 from latest graded price
        latest_gp = (card.graded_prices[-1] if card.graded_prices else None)
        psa10 = latest_gp.psa_10_cents if latest_gp else None
        psa10_pct = None
        if psa10 and market and market > 0:
            psa10_pct = round((psa10 - market) / market * 100, 1)

        items.append(CardSummary(
            id=card.product_id,
            name=card.name,
            set=card.group_name,
            num=card.card_number,
            image_url=card.image_url,
            market_price_cents=market,
            psa10_price_cents=psa10,
            psa10_premium_pct=psa10_pct,
            change_cents=change_cents,
            change_pct=change_pct,
        ))

    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@app.get("/api/cards/{product_id}", response_model=CardDetail)
def get_card(product_id: int, repo: SQLAlchemyRepository = Depends(get_repo)):
    card = repo.get_card(product_id)
    if not card:
        raise HTTPException(404, "Card not found")

    change_cents, change_pct = repo.get_price_change(product_id)
    latest_snap = card.price_snapshots[-1] if card.price_snapshots else None
    market = latest_snap.market_price_cents if latest_snap else None
    listing_count = latest_snap.listing_count if latest_snap else None

    latest_gp = card.graded_prices[-1] if card.graded_prices else None
    psa10 = latest_gp.psa_10_cents if latest_gp else None
    psa10_pct = None
    if psa10 and market and market > 0:
        psa10_pct = round((psa10 - market) / market * 100, 1)

    # Condition prices (industry standard multipliers)
    condition_prices = []
    if market:
        for cond, mult in [("NM", 1.0), ("LP", 0.76), ("MP", 0.60), ("HP", 0.40)]:
            condition_prices.append(ConditionPrice(
                condition=cond, price_cents=round(market * mult),
            ))

    return CardDetail(
        id=card.product_id,
        name=card.name,
        set=card.group_name,
        num=card.card_number,
        image_url=card.image_url,
        market_price_cents=market,
        psa10_price_cents=psa10,
        psa10_premium_pct=psa10_pct,
        change_cents=change_cents,
        change_pct=change_pct,
        category=card.category,
        rarity=card.rarity,
        url=card.url,
        condition_prices=condition_prices,
        listing_count=listing_count,
    )


@app.get("/api/cards/{product_id}/price-history", response_model=list[PriceHistoryPoint])
def card_price_history(
    product_id: int,
    repo: SQLAlchemyRepository = Depends(get_repo),
    period: str = "1M",
):
    snapshots = repo.get_price_history(product_id, period=period)
    return [
        PriceHistoryPoint(
            timestamp=s.timestamp,
            market_price_cents=s.market_price_cents,
            low_price_cents=s.low_price_cents,
            high_price_cents=s.high_price_cents,
        )
        for s in snapshots
    ]


# --- Products ---

@app.get("/api/products", response_model=PaginatedResponse[ProductSummary])
def list_products(
    repo: SQLAlchemyRepository = Depends(get_repo),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str | None = None,
    sort_by: str = "market_price",
    order: str = "desc",
):
    if sort_by not in VALID_PRODUCT_SORTS:
        raise HTTPException(422, f"Invalid sort_by. Valid: {VALID_PRODUCT_SORTS}")
    if order not in ("asc", "desc"):
        raise HTTPException(422, "Invalid order. Valid: asc, desc")

    products, total = repo.list_products(
        limit=limit, offset=offset, search=search,
        sort_by=sort_by, order=order,
    )

    items = []
    for prod in products:
        change_cents, change_pct = repo.get_price_change(prod.product_id)
        latest_snap = prod.price_snapshots[-1] if prod.price_snapshots else None
        market = latest_snap.market_price_cents if latest_snap else None

        items.append(ProductSummary(
            id=prod.product_id,
            name=prod.name,
            set=prod.group_name,
            image_url=prod.image_url,
            market_price_cents=market,
            change_cents=change_cents,
            change_pct=change_pct,
            release_date=prod.release_date,
        ))

    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@app.get("/api/products/{product_id}", response_model=ProductDetail)
def get_product(product_id: int, repo: SQLAlchemyRepository = Depends(get_repo)):
    prod = repo.get_product(product_id)
    if not prod:
        raise HTTPException(404, "Product not found")

    change_cents, change_pct = repo.get_price_change(product_id)
    latest_snap = prod.price_snapshots[-1] if prod.price_snapshots else None
    market = latest_snap.market_price_cents if latest_snap else None

    return ProductDetail(
        id=prod.product_id,
        name=prod.name,
        set=prod.group_name,
        image_url=prod.image_url,
        market_price_cents=market,
        change_cents=change_cents,
        change_pct=change_pct,
        release_date=prod.release_date,
        category=prod.category,
        url=prod.url,
    )


@app.get("/api/products/{product_id}/price-history", response_model=list[PriceHistoryPoint])
def product_price_history(
    product_id: int,
    repo: SQLAlchemyRepository = Depends(get_repo),
    period: str = "1M",
):
    snapshots = repo.get_price_history(product_id, period=period)
    return [
        PriceHistoryPoint(
            timestamp=s.timestamp,
            market_price_cents=s.market_price_cents,
            low_price_cents=s.low_price_cents,
            high_price_cents=s.high_price_cents,
        )
        for s in snapshots
    ]


# --- Search ---

@app.get("/api/search", response_model=list[SearchResult])
def search_products(
    q: str = "",
    type: str | None = None,
    repo: SQLAlchemyRepository = Depends(get_repo),
):
    if not q:
        return []
    results = repo.search(q, result_type=type)
    return [
        SearchResult(
            type="card" if r.product_type == "card" else "product",
            name=r.name,
            sub=r.group_name,
            price_cents=(r.price_snapshots[-1].market_price_cents
                        if r.price_snapshots else None),
            image_url=r.image_url,
        )
        for r in results
    ]


# --- Trends ---

@app.get("/api/trends/{keyword}", response_model=list[TrendPoint])
def get_trends(keyword: str, repo: SQLAlchemyRepository = Depends(get_repo)):
    points = repo.get_trend_data(keyword)
    return [
        TrendPoint(date=p.date, interest=p.interest, keyword=p.keyword)
        for p in points
    ]


# --- Grading ---

@app.get("/api/grading/{product_id}", response_model=list[GradingRow])
def get_grading(product_id: int, repo: SQLAlchemyRepository = Depends(get_repo)):
    graded = repo.get_grading(product_id)
    if not graded:
        return []

    latest = graded[0]  # Ordered by timestamp desc
    rows = []
    grade_map = [
        ("PSA 10", latest.psa_10_cents),
        ("Grade 9.5", latest.grade_9_5_cents),
        ("Grade 9", latest.grade_9_cents),
        ("Grade 8", latest.grade_8_cents),
        ("Grade 7", latest.grade_7_cents),
        ("Ungraded", latest.ungraded_cents),
    ]
    for grade, price in grade_map:
        if price is not None:
            rows.append(GradingRow(grade=grade, price_cents=price))

    return rows


# --- Population ---

@app.get("/api/population/{product_id}", response_model=list[PopulationRow])
def get_population(product_id: int, repo: SQLAlchemyRepository = Depends(get_repo)):
    reports = repo.get_population(product_id)
    if not reports:
        return []

    latest = reports[0]  # Ordered by timestamp desc
    rows = []
    pop_map = [
        ("PSA 10", latest.psa_10),
        ("PSA 9", latest.psa_9),
        ("PSA 8", latest.psa_8),
        ("BGS 10", latest.bgs_10),
        ("BGS 9.5", latest.bgs_9_5),
        ("CGC 10", latest.cgc_10),
        ("CGC 9.5", latest.cgc_9_5),
    ]
    for grade, count in pop_map:
        if count is not None:
            rows.append(PopulationRow(grade=grade, count=count))

    return rows


# --- Server Entry ---

def run_server():
    """Entry point for `pokeassistant-api` script."""
    import uvicorn
    uvicorn.run("pokeassistant.api:app", host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 4: Run API tests**

```bash
pytest tests/test_api.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/pokeassistant/api.py tests/test_api.py
git commit -m "feat: add FastAPI app with all endpoints

- Health check, card CRUD, product CRUD, price history
- Search, trends, grading, population endpoints
- CORS configured for localhost:5173
- Computed fields: price change, PSA premium, condition prices
- Pagination with sort_by/order support"
```

---

### Task 9: Update conftest.py

**Files:**
- Rewrite: `tests/conftest.py`

- [ ] **Step 1: Update conftest.py**

Replace `tests/conftest.py`:

```python
"""Shared test fixtures."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from pokeassistant.models import Base


@pytest.fixture
def engine():
    """In-memory SQLAlchemy engine with schema created."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine):
    """SQLAlchemy session for testing."""
    with Session(engine) as s:
        yield s


# Keep backward compat for any tests that still use mem_db
@pytest.fixture
def mem_db():
    """DEPRECATED — use session fixture instead."""
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # Import old schema for backward compat during migration
    try:
        from pokeassistant.db import init_db
        init_db(conn)
    except ImportError:
        pass
    yield conn
    conn.close()
```

- [ ] **Step 2: Run existing passing tests to check nothing breaks**

```bash
pytest tests/test_models.py tests/test_repository.py tests/test_api.py -v
```

Expected: All PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: update conftest.py with SQLAlchemy fixtures"
```

---

### Task 10: Update CLI to Use Repository

**Files:**
- Modify: `src/pokeassistant/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Rewrite cli.py to use repository**

Update `src/pokeassistant/cli.py`:
- Remove all imports from `pokeassistant.db`
- Import `get_engine`, `get_session_factory` from `pokeassistant.database`
- Import `SQLAlchemyRepository` from `pokeassistant.repositories`
- In `main()`, replace `conn = get_connection(db_path)` with:
  ```python
  engine = get_engine()
  SessionLocal = get_session_factory(engine)
  session = SessionLocal()
  repo = SQLAlchemyRepository(session)
  ```
- Replace all `insert_product(conn, ...)` with `repo.upsert_product(...)`
- Replace all `insert_price_snapshot(conn, ...)` with `repo.insert_price_snapshot(...)`
- Same for sale_records, trend_data, graded_prices, population_reports
- Replace `conn.close()` with `session.close()`
- Keep all scraper imports and argument parsing unchanged

- [ ] **Step 2: Update test_cli.py**

The argument parsing tests (`TestParseArgs`) stay unchanged. The `TestMainNoSource` tests stay unchanged — they test early exits that happen before any DB interaction, so the DB backend doesn't matter. No additional test changes needed for existing CLI tests.

- [ ] **Step 3: Run CLI tests**

```bash
pytest tests/test_cli.py -v
```

Expected: All PASS.

- [ ] **Step 4: Commit**

```bash
git add src/pokeassistant/cli.py tests/test_cli.py
git commit -m "refactor: update CLI to use SQLAlchemy repository

- Replace raw sqlite3 connection with SQLAlchemy session
- Use SQLAlchemyRepository for all data writes
- No changes to scraper logic or argument parsing"
```

---

### Task 11: Update Scrapers to Use New Models

**Files:**
- Modify: `src/pokeassistant/scrapers/tcgcsv.py`
- Modify: `src/pokeassistant/scrapers/tcgplayer.py`
- Modify: `src/pokeassistant/scrapers/pricecharting.py`
- Modify: `src/pokeassistant/scrapers/gemrate.py`
- Modify: `src/pokeassistant/scrapers/trends.py`

The scrapers already construct model instances with keyword arguments. The main changes are:
1. Model classes are now SQLAlchemy models instead of dataclasses (same constructor API)
2. `Product` no longer needs `created_at` passed (has a default)
3. `Product` instances should set `product_type` when known

- [ ] **Step 1: Update tcgcsv.py**

In `fetch_products()`, update the Product construction to include `product_type`:

```python
Product(
    product_id=p["productId"],
    name=p["name"],
    category="Pokemon",
    group_name=None,
    url=p.get("url"),
    image_url=p.get("imageUrl"),  # TCGCSV may provide this
    product_type="card" if "Single" in p.get("categoryName", "") else "sealed",
)
```

Note: The `created_at` field is now auto-populated by the SQLAlchemy default — remove any explicit `created_at` if present (currently it's set by the dataclass default_factory, which no longer exists).

- [ ] **Step 2: Update tcgplayer.py**

In `parse_product_details()`, add `product_type` classification:

```python
category = data.get("productLineUrlName", "Pokemon")
product_type = "card" if "single" in category.lower() else "sealed"
```

And include it in the Product constructor.

- [ ] **Step 3: Update pricecharting.py**

No model construction changes needed — `GradedPrice` constructor is the same. Just verify imports still work (they import from `pokeassistant.models` which is now SQLAlchemy).

- [ ] **Step 4: Update gemrate.py**

No model construction changes needed — `PopulationReport` constructor is the same.

- [ ] **Step 5: Update trends.py**

No model construction changes needed — `TrendDataPoint` constructor is the same.

- [ ] **Step 6: Run all scraper tests**

```bash
pytest tests/test_tcgcsv.py tests/test_tcgplayer.py tests/test_pricecharting.py tests/test_gemrate.py tests/test_trends.py -v
```

Expected: All PASS (scraper tests use fixtures/mocks, not real DB).

- [ ] **Step 7: Commit**

```bash
git add src/pokeassistant/scrapers/
git commit -m "refactor: update scrapers for SQLAlchemy models

- Add product_type classification to tcgcsv and tcgplayer
- No changes needed for pricecharting, gemrate, trends
- created_at now auto-populated by SQLAlchemy default"
```

---

### Task 12: Delete Old db.py and test_db.py

**Files:**
- Delete: `src/pokeassistant/db.py`
- Delete: `tests/test_db.py`

- [ ] **Step 1: Verify nothing imports db.py anymore**

```bash
cd /home/ttran/projects/pokeAssistant
grep -r "from pokeassistant.db import\|from pokeassistant import db\|import pokeassistant.db" src/ tests/ --include="*.py" | grep -v __pycache__
```

Expected: Only `tests/conftest.py` (the backward-compat fixture) and possibly the old `test_db.py`. If cli.py or any scraper still imports db.py, fix those first.

- [ ] **Step 2: Delete the files**

```bash
rm src/pokeassistant/db.py tests/test_db.py
```

- [ ] **Step 3: Clean up conftest.py backward-compat fixture**

Remove the `mem_db` fixture from `tests/conftest.py` since nothing uses it anymore.

- [ ] **Step 4: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests PASS. No imports of db.py remain.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: delete old db.py and test_db.py

Replaced by:
- src/pokeassistant/database.py (engine/session factory)
- src/pokeassistant/repositories/sqlalchemy_repo.py (all CRUD)
- tests/test_repository.py (comprehensive repository tests)"
```

---

### Task 13: Final Integration Test

**Files:**
- No new files — end-to-end verification

- [ ] **Step 1: Run the full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests PASS.

- [ ] **Step 2: Start the API server and test manually**

```bash
# Terminal 1: Start API
cd /home/ttran/projects/pokeAssistant
pokeassistant-api &
sleep 2

# Terminal 2: Test endpoints
curl -s http://localhost:8000/api/health | python -m json.tool
curl -s http://localhost:8000/api/cards | python -m json.tool
curl -s http://localhost:8000/api/products | python -m json.tool
curl -s "http://localhost:8000/api/search?q=test" | python -m json.tool

# Kill the server
kill %1
```

Expected: Health returns `{"status":"ok","db":"connected"}`. Cards/products return empty paginated responses (no data scraped yet). Search returns `[]`.

- [ ] **Step 3: Test CORS headers**

```bash
curl -s -I -X OPTIONS http://localhost:8000/api/cards \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" 2>&1 | grep -i "access-control"
```

Expected: `access-control-allow-origin: http://localhost:5173`

- [ ] **Step 4: Commit final state**

```bash
git add -A
git commit -m "chore: FastAPI API layer migration complete

Summary:
- SQLAlchemy ORM models replace dataclass models
- Repository pattern with abstract interface
- FastAPI with 11 endpoints (health, cards, products, search, trends, grading, population)
- CORS configured for React frontend
- CLI updated to use repository
- All scrapers updated for new model constructors
- Old db.py removed
- Full test coverage: models, repository, API, CLI, scrapers"
```

---

## Dependency Graph

```
Task 0 (baseline)
  └── Task 1 (deps)
       └── Task 2 (models + tests)
            ├── Task 3 (database.py)
            │    └── Task 5 (repository interface)
            │         └── Task 6 (repo write ops + tests)
            │              └── Task 7 (repo read ops + tests)
            │                   └── Task 8 (api.py + tests)
            │                        └── Task 9 (conftest)
            │                             └── Task 10 (CLI update)
            │                                  └── Task 11 (scraper updates)
            │                                       └── Task 12 (delete db.py)
            │                                            └── Task 13 (integration)
            └── Task 4 (schemas — can run in parallel with 3-5)
```
