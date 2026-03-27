# FastAPI API Layer — Design Spec

**Date:** 2026-03-27  
**Status:** Approved  
**Goal:** Build a FastAPI API layer to connect the React frontend ("Pack Magik") to the existing Python/SQLite backend, migrating to SQLAlchemy ORM with a repository pattern for future DB swappability (e.g., Supabase/Postgres).

---

## Context

### Current State
- **Backend:** Python CLI tool with 5 scrapers (TCGPlayer, TCGCSV, PriceCharting, GemRate, Google Trends) that save data to a local SQLite DB (`data/pokeassistant.db`).
- **Frontend:** React + Vite app on `localhost:5173` with a comprehensive UI (Discover, Card Detail, Product Detail, Collection views). **All data is hardcoded** as JavaScript constants (~1,200 lines in App.jsx).
- **Database:** 6 tables (products, price_snapshots, sale_records, trend_data, graded_prices, population_reports) using raw `sqlite3` with dataclass models.
- **No API exists** — frontend and backend are disconnected.

### What This Spec Covers
1. Migrate data layer from raw sqlite3 + dataclasses to **SQLAlchemy ORM**
2. Add **repository pattern** for DB backend swappability
3. Extend schema with **missing fields** needed by frontend (image_url, card_number, product_type, rarity)
4. Create **FastAPI endpoints** serving all 6 data tables with computed fields
5. Configure **CORS** for React dev server
6. Update **CLI and scrapers** to use the new data layer
7. Update **tests**

### What This Spec Does NOT Cover
See [Future Backlog](#future-backlog) for deferred items.

---

## Architecture

```
┌──────────────────────┐     HTTP/JSON      ┌──────────────────────────┐
│   React Frontend     │ ◄────────────────► │     FastAPI (api.py)     │
│   (localhost:5173)   │     CORS enabled    │     (localhost:8000)     │
└──────────────────────┘                    └──────────┬───────────────┘
                                                       │
                                            ┌──────────▼───────────────┐
                                            │   Pydantic Schemas       │
                                            │   (schemas.py)           │
                                            └──────────┬───────────────┘
                                                       │
                                            ┌──────────▼───────────────┐
                                            │   Repository Interface   │
                                            │   (repository.py)        │
                                            └──────────┬───────────────┘
                                                       │
                                     ┌─────────────────┼─────────────────┐
                                     │                                   │
                          ┌──────────▼───────────┐            ┌──────────▼──────────┐
                          │  SQLAlchemy Repo      │            │  Future: Supabase   │
                          │  (sqlalchemy_repo.py) │            │  Repo               │
                          └──────────┬────────────┘            └─────────────────────┘
                                     │
                          ┌──────────▼────────────┐
                          │  SQLite / Postgres     │
                          │  (via SQLAlchemy)       │
                          └────────────────────────┘

CLI (cli.py) and Scrapers also use the Repository Interface.
```

---

## 1. Schema Extensions

### New Columns on `products` Table

| Column | Type | Nullable | Purpose |
|--------|------|----------|---------|
| `image_url` | TEXT | Yes | Card art or product box image URL |
| `card_number` | TEXT | Yes | Set number, e.g. "284/217" |
| `product_type` | TEXT | Yes | "card" or "sealed" — distinguishes singles from sealed products |
| `rarity` | TEXT | Yes | Card rarity for future pull rate calculations |

### New Column on `population_reports` Table

| Column | Type | Nullable | Purpose |
|--------|------|----------|---------|
| `product_id` | INTEGER (FK) | Yes | Links population data to a product, enabling joins from card detail views |

### Existing Tables (Unchanged Schema)
- `price_snapshots` — no changes
- `sale_records` — no changes
- `trend_data` — no changes
- `graded_prices` — no changes (already has `product_id`)

### Computed Fields (Not Stored)
These are calculated at query time in the API/repository layer:

| Field | Computation |
|-------|-------------|
| `price_change_cents` | Latest snapshot market_price - previous snapshot market_price |
| `price_change_pct` | `(change / previous) * 100` |
| `psa10_premium_pct` | `(psa10_price - market_price) / market_price * 100` from graded_prices |
| `condition_prices` | NM = market, LP = 76%, MP = 60%, HP = 40% of market |
| `grading_trend` | Compare latest graded_price to previous entry: "up" if higher, "down" if lower, "flat" if within 2% |
| `product_type` | Set by scrapers: TCGPlayer/TCGCSV categories containing "Single" → "card", otherwise → "sealed" |

---

## 2. SQLAlchemy ORM Models

**File:** `src/pokeassistant/models.py` (replaces existing dataclasses)

```python
from sqlalchemy import Column, Integer, Text, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, relationship

class Base(DeclarativeBase):
    pass

class Product(Base):
    __tablename__ = "products"
    product_id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    category = Column(Text)
    group_name = Column(Text)
    url = Column(Text)
    image_url = Column(Text)           # NEW
    card_number = Column(Text)          # NEW
    product_type = Column(Text)         # NEW: "card" or "sealed"
    rarity = Column(Text)              # NEW
    created_at = Column(Text, nullable=False)
    
    price_snapshots = relationship("PriceSnapshot", back_populates="product")
    sale_records = relationship("SaleRecord", back_populates="product")

class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    timestamp = Column(Text, nullable=False)
    source = Column(Text, nullable=False)
    low_price_cents = Column(Integer)
    market_price_cents = Column(Integer)
    high_price_cents = Column(Integer)
    listing_count = Column(Integer)
    __table_args__ = (UniqueConstraint("product_id", "timestamp", "source"),)
    
    product = relationship("Product", back_populates="price_snapshots")

class SaleRecord(Base):
    __tablename__ = "sale_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    sale_date = Column(Text, nullable=False)
    condition = Column(Text)
    variant = Column(Text)
    price_cents = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    source = Column(Text, nullable=False)
    __table_args__ = (UniqueConstraint("product_id", "sale_date", "condition", "variant", "price_cents"),)
    
    product = relationship("Product", back_populates="sale_records")

class TrendDataPoint(Base):
    __tablename__ = "trend_data"
    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(Text, nullable=False)
    date = Column(Text, nullable=False)
    interest = Column(Integer, nullable=False)
    source = Column(Text, nullable=False)
    __table_args__ = (UniqueConstraint("keyword", "date"),)

class GradedPrice(Base):
    __tablename__ = "graded_prices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer)
    card_name = Column(Text, nullable=False)
    source = Column(Text, nullable=False)
    timestamp = Column(Text, nullable=False)
    ungraded_cents = Column(Integer)
    grade_7_cents = Column(Integer)
    grade_8_cents = Column(Integer)
    grade_9_cents = Column(Integer)
    grade_9_5_cents = Column(Integer)
    psa_10_cents = Column(Integer)
    bgs_10_cents = Column(Integer)
    cgc_10_cents = Column(Integer)
    sgc_10_cents = Column(Integer)
    pricecharting_url = Column(Text)
    __table_args__ = (UniqueConstraint("card_name", "timestamp", "source"),)

class PopulationReport(Base):
    __tablename__ = "population_reports"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id"))  # NEW — enables join by product_id
    card_name = Column(Text, nullable=False)
    gemrate_id = Column(Text, nullable=False)
    source = Column(Text, nullable=False)
    timestamp = Column(Text, nullable=False)
    total_population = Column(Integer, nullable=False)
    psa_10 = Column(Integer)
    psa_9 = Column(Integer)
    psa_8 = Column(Integer)
    bgs_10 = Column(Integer)
    bgs_9_5 = Column(Integer)
    cgc_10 = Column(Integer)
    cgc_9_5 = Column(Integer)
    gem_rate = Column(Float)
    __table_args__ = (UniqueConstraint("gemrate_id", "timestamp"),)
```

The `dollars_to_cents` utility function stays as a standalone helper.

---

## 3. Database Engine / Session Factory

**File:** `src/pokeassistant/database.py`

**Migration note:** `Base.metadata.create_all()` creates missing tables but won't ALTER existing ones. Since the database is currently empty (no data has been scraped yet), this is not a problem. For future schema changes after data exists, use Alembic or manual ALTER TABLE statements.

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from pokeassistant.config import get_db_path
from pokeassistant.models import Base

def get_engine(db_url: str | None = None):
    if db_url is None:
        db_url = f"sqlite:///{get_db_path()}"
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    return engine

def get_session_factory(engine) -> sessionmaker:
    return sessionmaker(bind=engine)

# For FastAPI dependency injection
def get_db() -> Session:
    engine = get_engine()
    SessionLocal = get_session_factory(engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

---

## 4. Pydantic Response Schemas

**File:** `src/pokeassistant/schemas.py`

```python
from pydantic import BaseModel
from typing import Optional

# --- Cards ---
class CardSummary(BaseModel):
    id: int
    name: str
    set: str | None           # group_name
    num: str | None           # card_number
    image_url: str | None
    market_price_cents: int | None
    psa10_price_cents: int | None
    psa10_premium_pct: float | None   # computed
    change_cents: int | None          # computed
    change_pct: float | None          # computed

class ConditionPrice(BaseModel):
    condition: str        # NM, LP, MP, HP
    price_cents: int

class CardDetail(CardSummary):
    category: str | None
    rarity: str | None
    url: str | None
    condition_prices: list[ConditionPrice]
    listing_count: int | None

# --- Products ---
class ProductSummary(BaseModel):
    id: int
    name: str
    set: str | None
    image_url: str | None
    market_price_cents: int | None
    change_cents: int | None
    change_pct: float | None

class ProductDetail(ProductSummary):
    category: str | None
    url: str | None

# --- Price History ---
class PriceHistoryPoint(BaseModel):
    timestamp: str
    market_price_cents: int | None
    low_price_cents: int | None
    high_price_cents: int | None

# --- Grading ---
class GradingRow(BaseModel):
    grade: str
    population: int | None
    pct: float | None
    price_cents: int | None
    trend: str | None         # "up", "down", "flat"

# --- Population ---
class PopulationRow(BaseModel):
    grade: str
    count: int

# --- Trends ---
class TrendPoint(BaseModel):
    date: str
    interest: int
    keyword: str

# --- Search ---
class SearchResult(BaseModel):
    type: str                 # "card", "product", "set"
    name: str
    sub: str | None
    price_cents: int | None
    image_url: str | None

# --- Pagination ---
class PaginatedResponse(BaseModel):
    items: list
    total: int
    limit: int
    offset: int
```

---

## 5. Repository Interface

**File:** `src/pokeassistant/repository.py`

```python
from abc import ABC, abstractmethod

class CardRepository(ABC):
    # Read - Cards
    @abstractmethod
    def list_cards(self, limit=50, offset=0, category=None, search=None) -> tuple[list, int]: ...
    
    @abstractmethod
    def get_card(self, product_id: int): ...
    
    @abstractmethod
    def get_price_history(self, product_id: int, period: str = "1M") -> list: ...
    
    @abstractmethod
    def get_price_change(self, product_id: int) -> tuple[int | None, float | None]: ...
    
    # Read - Products (sealed)
    @abstractmethod
    def list_products(self, limit=50, offset=0, search=None) -> tuple[list, int]: ...
    
    @abstractmethod
    def get_product(self, product_id: int): ...
    
    # Read - Grading & Population
    @abstractmethod
    def get_grading(self, product_id: int) -> list: ...
    
    @abstractmethod
    def get_population(self, product_id: int) -> list: ...
    
    # Read - Trends
    @abstractmethod
    def get_trend_data(self, keyword: str) -> list: ...
    
    # Read - Search
    @abstractmethod
    def search(self, query: str, result_type: str | None = None) -> list: ...
    
    # Write (used by CLI/scrapers) — accept SQLAlchemy model instances
    @abstractmethod
    def upsert_product(self, product: "Product") -> None: ...
    
    @abstractmethod
    def insert_price_snapshot(self, snapshot: "PriceSnapshot") -> None: ...
    
    @abstractmethod
    def insert_sale_record(self, sale: "SaleRecord") -> None: ...
    
    @abstractmethod
    def insert_trend_data(self, trend: "TrendDataPoint") -> None: ...
    
    @abstractmethod
    def insert_graded_price(self, graded: "GradedPrice") -> None: ...
    
    @abstractmethod
    def insert_population_report(self, report: "PopulationReport") -> None: ...
```

---

## 6. SQLAlchemy Repository Implementation

**File:** `src/pokeassistant/repositories/sqlalchemy_repo.py`

Implements `CardRepository` using SQLAlchemy sessions. Key behaviors:

- **`list_cards`**: Queries `products WHERE product_type = 'card'`, joins latest `price_snapshot` for market price, joins latest `graded_prices` for PSA10, computes change from last two snapshots.
- **`list_products`**: Same but `product_type = 'sealed'`.
- **`get_price_history`**: Filters `price_snapshots` by product_id and period (1M = 30 days, 3M = 90, etc.).
- **`get_price_change`**: Compares latest two snapshots for the product.
- **`search`**: `LIKE` query on product name, optionally filtered by type.
- **Write methods**: Map to SQLAlchemy `session.merge()` / `session.add()` with commit.

---

## 7. FastAPI Application

**File:** `src/pokeassistant/api.py`

```python
from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="PokeAssistant API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoints listed in next section
```

### Endpoint Definitions

| Method | Path | Response | Query Params |
|--------|------|----------|-------------|
| GET | `/api/cards` | `PaginatedResponse[CardSummary]` | `limit`, `offset`, `category`, `search` |
| GET | `/api/cards/{id}` | `CardDetail` | — |
| GET | `/api/cards/{id}/price-history` | `PriceHistoryPoint[]` | `period` (1M/3M/6M/1Y/ALL) |
| GET | `/api/products` | `PaginatedResponse[ProductSummary]` | `limit`, `offset`, `search` |
| GET | `/api/products/{id}` | `ProductDetail` | — |
| GET | `/api/products/{id}/price-history` | `PriceHistoryPoint[]` | `period` |
| GET | `/api/search` | `SearchResult[]` | `q`, `type` (card/product/all) |
| GET | `/api/trends/{keyword}` | `TrendPoint[]` | — |
| GET | `/api/grading/{product_id}` | `GradingRow[]` | — |
| GET | `/api/population/{product_id}` | `PopulationRow[]` | — |

### Error Handling
- 404 for missing products/cards
- 422 for invalid query params (FastAPI default)
- All monetary values returned as **cents** (integers) — frontend converts to dollars

---

## 8. CLI + Scraper Updates

### CLI (`cli.py`)
- Replace direct `db.py` function calls with repository methods
- Replace `get_connection()` with `get_engine()` + session
- The scraper results still flow through the same pipeline, just using repository.upsert_product() etc.

### Scrapers
- Currently import from `pokeassistant.models` (dataclasses) to construct results
- Update to construct SQLAlchemy model instances instead
- Core scraping logic (HTTP requests, HTML parsing) stays unchanged
- Each scraper returns model instances that the CLI passes to the repository

---

## 9. Dependencies

Add to `pyproject.toml`:
```toml
dependencies = [
    # ... existing ...
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "sqlalchemy>=2.0",
    "pydantic>=2.0",
]
```

Add script entry:
```toml
[project.scripts]
pokeassistant = "pokeassistant.cli:main"
pokeassistant-api = "pokeassistant.api:run_server"
```

---

## 10. File Structure

```
src/pokeassistant/
├── __init__.py              # unchanged
├── config.py                # unchanged (DB path, constants)
├── models.py                # REWRITTEN → SQLAlchemy ORM models
├── schemas.py               # NEW → Pydantic response schemas
├── database.py              # NEW → Engine/session factory
├── repository.py            # NEW → Abstract repository interface
├── repositories/
│   ├── __init__.py          # NEW
│   └── sqlalchemy_repo.py   # NEW → SQLAlchemy implementation
├── api.py                   # NEW → FastAPI app + endpoints + CORS
├── cli.py                   # UPDATED → use repository
└── scrapers/                # UPDATED → use new SQLAlchemy models
    ├── __init__.py
    ├── tcgplayer.py
    ├── tcgcsv.py
    ├── pricecharting.py
    ├── gemrate.py
    └── trends.py

tests/
├── conftest.py              # UPDATED → SQLAlchemy test fixtures
├── test_models.py           # UPDATED → SQLAlchemy model tests
├── test_repository.py       # NEW → replaces test_db.py
├── test_api.py              # NEW → FastAPI endpoint tests (TestClient)
├── test_cli.py              # UPDATED
├── test_db.py               # DELETED (replaced by test_repository.py)
└── ... (scraper tests — minimal changes)
```

---

## 11. Testing Strategy

- **test_repository.py**: Uses in-memory SQLite (`sqlite:///:memory:`) to test all repository methods (read + write).
- **test_api.py**: Uses FastAPI `TestClient` with an in-memory DB, tests all endpoints including edge cases (404s, empty data, pagination).
- **Scraper tests**: Remain mostly fixture-based; just update model construction from dataclass to SQLAlchemy.
- **test_cli.py**: Update to mock the repository instead of raw db functions.

---

## Future Backlog

Items deferred from this spec, to be addressed in future iterations:

### Data Gaps (Frontend needs, backend doesn't have)
- [ ] **Pull rates / pull odds** — Editorial/community data for sealed products. Needs a data source or manual entry system.
- [ ] **Expected Value (EV)** — Requires: knowing which cards are in a product + their pull rates + market prices. Needs a `product_contents` junction table.
- [ ] **Market Sentiment** — Reddit, Twitter/X, eBay velocity, YouTube scraping. Major feature requiring new scrapers + NLP/sentiment analysis.
- [ ] **Collection / Portfolio tracking** — Needs `user_collections` table, potentially auth system. Supports the "Add to Collection" button in frontend.
- [ ] **Rip vs Flip analysis** — Depends on EV calculation + sealed product price tracking.
- [ ] **Buy Signal analysis** — Composite score from price momentum, sentiment, volume. Needs multiple data sources feeding a scoring model.
- [ ] **Gradeability indicators** — Analysis of centering, surface quality signals. Highly specialized.
- [ ] **Active marketplace listings** — Real-time listing feed from TCGPlayer/eBay. Needs persistent scraping or API access.

### Infrastructure
- [ ] **Supabase/Postgres migration** — Write a `SupabaseRepository` implementing `CardRepository`. SQLAlchemy makes this near-trivial (change connection string).
- [ ] **Authentication** — Required for collection tracking, user preferences, alerts.
- [ ] **Alerts system** — Price threshold alerts, stock notifications. Needs background job scheduler.
- [ ] **Caching layer** — Redis or in-memory cache for frequently accessed endpoints.
- [ ] **Rate limiting** — Protect API from abuse.
- [ ] **Background scraper scheduler** — Cron/Celery for periodic data refresh instead of manual CLI runs.

### Frontend
- [ ] **Wire up API calls** — Replace all hardcoded JS constants with `fetch()` calls to the API.
- [ ] **Error states** — Loading spinners, error boundaries, empty states for API failures.
- [ ] **Insights page** — Currently a stub. Needs trend visualization + portfolio analytics.
- [ ] **Pack Battles page** — Currently a stub. Needs game/comparison logic.
- [ ] **Alerts page** — Currently a stub. Depends on alerts infrastructure.
