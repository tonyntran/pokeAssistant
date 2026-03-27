# FastAPI API Layer — Design Spec

**Date:** 2026-03-27  
**Status:** Approved (Rev 2 — post user review)  
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
3. Extend schema with **missing fields** needed by frontend (image_url, card_number, product_type, rarity, release_date)
4. Create **FastAPI endpoints** serving all 6 data tables with computed fields
5. Configure **CORS** for React dev server
6. Update **CLI and scrapers** to use the new data layer
7. Update **tests**

### What This Spec Does NOT Cover
See [Future Backlog](#future-backlog) for deferred items.

### Explicitly Out of Scope for This Build
- **"Cards Inside" a product** — The frontend's `PRODUCT_CARDS_INSIDE` grid requires a `product_contents` junction table and pull rate data that doesn't exist yet. The `ProductDetail` API response will **not** include cards-inside data. The frontend should keep this section hardcoded or show an empty state until the backlog item ships.
- **Market Sentiment** — No sentiment scraping infrastructure exists. Frontend keeps hardcoded `SENTIMENT_DATA`.
- **Collection / Portfolio** — No user or collection tables. Frontend keeps the empty-state placeholder.
- **Pull rates, pull odds, EV, Rip vs Flip** — All require data sources we don't have. Frontend keeps hardcoded values.

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
| `release_date` | Date | Yes | Enables "Sort: Release" on products (SQLAlchemy `Date` type) |

### New Column on `population_reports` Table

| Column | Type | Nullable | Purpose |
|--------|------|----------|---------|
| `product_id` | INTEGER (FK) | Yes | Links population data to a product, enabling joins from card detail views |

### Existing Tables (Unchanged Schema)
- `price_snapshots` — no changes
- `sale_records` — no changes
- `trend_data` — no changes
- `graded_prices` — no changes to stored columns, but `product_id` gets a FK constraint (see Models section)

### `product_type` Classification

This is a **stored** column set by scrapers. Classification rules:

| TCGPlayer/TCGCSV Category | product_type | Examples |
|---|---|---|
| Contains "Single" | `"card"` | "Pokemon Single" |
| Everything else | `"sealed"` | "Pokemon Booster Box", "Pokemon Elite Trainer Box", "Pokemon Tin", "Pokemon Bundle", "Pokemon Code Card" |

**Known simplification:** The `"sealed"` bucket includes code cards, accessories, and display boxes alongside booster products. This is acceptable for now — a future `product_subtype` column can further classify sealed products when EV/pull-rate calculations require it.

### Image URL Strategy

The `image_url` field is populated by scrapers from these sources (in priority order):
1. **TCGCSV** — provides product image URLs in their API response
2. **TCGPlayer scraper** — extracts the product image from the page
3. **Fallback** — The frontend already uses `images.pokemontcg.io` URLs in its hardcoded data. For cards not yet scraped, the frontend's `onError` handlers show placeholder images.

If a scraper doesn't have an image URL, the field is left `null`. The frontend must handle `null` gracefully (it already does via `onError` img handlers).

### Timestamp/Date Column Types

All timestamp and date columns use **SQLAlchemy's `DateTime` and `Date` types** (not `Text`). This means:
- **Python side:** Scrapers pass native `datetime` and `date` objects (which they already do). No `.isoformat()` conversion needed.
- **SQLite storage:** SQLAlchemy automatically converts to/from ISO 8601 strings under the hood. Sorting works correctly.
- **Postgres/Supabase:** When we migrate, `DateTime`/`Date` map directly to native timestamp/date columns. No migration of stored data needed.

Scrapers must ensure all timestamps are timezone-naive or consistently UTC. The existing scrapers all use `datetime.now()` and `date.fromisoformat()`, which produce naive datetimes — this is fine for now.

### Computed Fields (Not Stored)
These are calculated at query time in the API/repository layer:

| Field | Computation |
|-------|-------------|
| `price_change_cents` | Latest snapshot `market_price_cents` − previous snapshot `market_price_cents` |
| `price_change_pct` | `(change / previous) * 100` |
| `psa10_premium_pct` | `(psa10_price - market_price) / market_price * 100` from graded_prices |
| `condition_prices` | NM = market, LP = 76%, MP = 60%, HP = 40% of market |
| `grading_trend` | Compare latest graded_price to previous entry for same grade: "up" if higher, "down" if lower, "flat" if within 2% |

---

## 2. SQLAlchemy ORM Models

**File:** `src/pokeassistant/models.py` (replaces existing dataclasses)

```python
from datetime import datetime, date as date_type

from sqlalchemy import Column, Integer, Text, Float, Date, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, relationship


def dollars_to_cents(value) -> int | None:
    """Convert a dollar amount to cents (integer).
    Accepts float, int, string, or None. Returns None if input is None.
    """
    if value is None:
        return None
    return round(float(value) * 100)


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"
    product_id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    category = Column(Text)
    group_name = Column(Text)
    url = Column(Text)
    image_url = Column(Text)            # NEW
    card_number = Column(Text)           # NEW
    product_type = Column(Text)          # NEW: "card" or "sealed"
    rarity = Column(Text)               # NEW
    release_date = Column(Date)          # NEW
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    #                                     ^^^^^^^ Python-side default
    # Scrapers can omit created_at — SQLAlchemy fills it automatically.
    # Existing scraper code like Product(product_id=1, name="X") just works.

    price_snapshots = relationship("PriceSnapshot", back_populates="product")
    sale_records = relationship("SaleRecord", back_populates="product")
    graded_prices = relationship("GradedPrice", back_populates="product")
    population_reports = relationship("PopulationReport", back_populates="product")

    def __repr__(self):
        return f"<Product(id={self.product_id}, name='{self.name}', type='{self.product_type}')>"


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    source = Column(Text, nullable=False)
    low_price_cents = Column(Integer)
    market_price_cents = Column(Integer)
    high_price_cents = Column(Integer)
    listing_count = Column(Integer)
    __table_args__ = (UniqueConstraint("product_id", "timestamp", "source"),)

    product = relationship("Product", back_populates="price_snapshots")

    def __repr__(self):
        return f"<PriceSnapshot(product_id={self.product_id}, market={self.market_price_cents}, ts={self.timestamp})>"


class SaleRecord(Base):
    __tablename__ = "sale_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    sale_date = Column(Date, nullable=False)
    condition = Column(Text)
    variant = Column(Text)
    price_cents = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    source = Column(Text, nullable=False)
    __table_args__ = (UniqueConstraint("product_id", "sale_date", "condition", "variant", "price_cents"),)

    product = relationship("Product", back_populates="sale_records")

    def __repr__(self):
        return f"<SaleRecord(product_id={self.product_id}, price={self.price_cents}, date={self.sale_date})>"


class TrendDataPoint(Base):
    __tablename__ = "trend_data"
    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(Text, nullable=False)
    date = Column(Date, nullable=False)
    interest = Column(Integer, nullable=False)
    source = Column(Text, nullable=False)
    __table_args__ = (UniqueConstraint("keyword", "date"),)

    def __repr__(self):
        return f"<TrendDataPoint(keyword='{self.keyword}', date={self.date}, interest={self.interest})>"


class GradedPrice(Base):
    __tablename__ = "graded_prices"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id"))  # FK added
    card_name = Column(Text, nullable=False)
    source = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
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

    product = relationship("Product", back_populates="graded_prices")

    def __repr__(self):
        return f"<GradedPrice(card='{self.card_name}', psa10={self.psa_10_cents})>"


class PopulationReport(Base):
    __tablename__ = "population_reports"
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.product_id"))  # NEW
    card_name = Column(Text, nullable=False)
    gemrate_id = Column(Text, nullable=False)
    source = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False)
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

    product = relationship("Product", back_populates="population_reports")

    def __repr__(self):
        return f"<PopulationReport(card='{self.card_name}', total={self.total_population})>"
```

---

## 3. Database Engine / Session Factory

**File:** `src/pokeassistant/database.py`

**Migration note:** `Base.metadata.create_all()` creates missing tables but won't ALTER existing ones. Since the database is currently empty (no data has been scraped yet), this is not a problem. For future schema changes after data exists, use Alembic or manual ALTER TABLE statements.

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from pokeassistant.config import get_db_path
from pokeassistant.models import Base

# Module-level singleton — engine is created once and reused across all requests.
# create_engine() is expensive (sets up connection pool). Do NOT call it per-request.
_engine = None
_SessionLocal = None


def get_engine(db_url: str | None = None):
    """Get or create the singleton SQLAlchemy engine.
    
    IMPORTANT: Once created, the engine URL is fixed for the process lifetime.
    Passing a different db_url after first creation is silently ignored.
    To switch databases (e.g., in tests), call reset_engine() first:
    
        reset_engine()
        engine = get_engine("sqlite:///:memory:")
    
    The CLI and API both rely on POKEASSISTANT_DB_PATH env var (via get_db_path())
    to determine the DB location, which is read at first-call time.
    """
    global _engine
    if _engine is None:
        if db_url is None:
            db_url = f"sqlite:///{get_db_path()}"
        echo = os.environ.get("POKEASSISTANT_DEBUG", "").lower() in ("1", "true")
        _engine = create_engine(db_url, echo=echo)
        Base.metadata.create_all(_engine)
    return _engine


def get_session_factory(engine=None) -> sessionmaker:
    """Get or create the singleton session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        if engine is None:
            engine = get_engine()
        _SessionLocal = sessionmaker(bind=engine)
    return _SessionLocal


def reset_engine():
    """Reset the engine and session factory singletons.
    
    Required before switching databases (e.g., in tests).
    After calling this, the next get_engine() call creates a fresh engine.
    """
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()  # Close all pooled connections
    _engine = None
    _SessionLocal = None


def get_db():
    """FastAPI dependency — yields a session per request, auto-closes after."""
    SessionLocal = get_session_factory()
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
from datetime import datetime, date
from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")


# --- Pagination ---

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


# --- Cards ---

class CardSummary(BaseModel):
    id: int
    name: str
    set: str | None             # group_name
    num: str | None             # card_number
    image_url: str | None
    market_price_cents: int | None
    psa10_price_cents: int | None
    psa10_premium_pct: float | None    # computed
    change_cents: int | None           # computed
    change_pct: float | None           # computed


class ConditionPrice(BaseModel):
    condition: str          # NM, LP, MP, HP
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
    release_date: date | None       # Pydantic serializes as "YYYY-MM-DD" in JSON


class ProductDetail(ProductSummary):
    category: str | None
    url: str | None
    # NOTE: cards_inside is NOT included — see "Explicitly Out of Scope"


# --- Price History ---

class PriceHistoryPoint(BaseModel):
    timestamp: datetime             # Pydantic serializes as ISO 8601 in JSON
    market_price_cents: int | None
    low_price_cents: int | None
    high_price_cents: int | None


# --- Grading ---

class GradingRow(BaseModel):
    grade: str
    population: int | None
    pct: float | None
    price_cents: int | None
    trend: str | None           # "up", "down", "flat"


# --- Population ---

class PopulationRow(BaseModel):
    grade: str
    count: int


# --- Trends ---

class TrendPoint(BaseModel):
    date: date                      # Pydantic serializes as "YYYY-MM-DD" in JSON
    interest: int
    keyword: str


# --- Search ---

class SearchResult(BaseModel):
    type: str                   # "card", "product", "set"
    name: str
    sub: str | None
    price_cents: int | None
    image_url: str | None


# --- Health ---

class HealthResponse(BaseModel):
    status: str
    db: str
```

---

## 5. Repository Interface

**File:** `src/pokeassistant/repository.py`

```python
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pokeassistant.models import (
        Product, PriceSnapshot, SaleRecord,
        TrendDataPoint, GradedPrice, PopulationReport,
    )


class CardRepository(ABC):
    """Abstract interface for all data access.
    
    Implementations: SQLAlchemyRepository (now), SupabaseRepository (future).
    """

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

    # --- Write (used by CLI/scrapers) ---

    @abstractmethod
    def upsert_product(self, product: "Product") -> None:
        """Insert or update a product.
        
        Upsert semantics: If a product with matching product_id exists,
        update name unconditionally. Update image_url, card_number,
        product_type, rarity, release_date, category, group_name, url
        only if the incoming value is not None (preserve existing data
        from other scrapers). If no match, insert.
        """
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

---

## 6. SQLAlchemy Repository Implementation

**File:** `src/pokeassistant/repositories/sqlalchemy_repo.py`

Implements `CardRepository` using SQLAlchemy sessions. Key behaviors:

### Read Operations

- **`list_cards`**: Queries `products WHERE product_type = 'card'`, joins latest `price_snapshot` for market price, joins latest `graded_prices` for PSA10, computes change from last two snapshots. Supports `sort_by` (`market_price`, `name`, `change`) and `order` (`asc`, `desc`).
- **`list_products`**: Same pattern but `product_type = 'sealed'`. Supports additional `sort_by=release_date` for "Sort: Release" in the frontend.
- **`get_price_history`**: Filters `price_snapshots` by product_id and period (1M = 30 days, 3M = 90, 6M = 180, 1Y = 365, ALL = no limit).
- **`get_price_change`**: Fetches the two most recent snapshots for a product, computes delta in cents and percentage.
- **`search`**: `LIKE '%query%'` on `products.name`, optionally filtered by `product_type`. Returns up to 20 results ordered by market price.

### Write Operations — Upsert Behavior

**`upsert_product`** uses an explicit query-then-merge pattern (NOT blind `session.merge()`):

```python
def upsert_product(self, product: Product) -> None:
    existing = self.session.get(Product, product.product_id)
    if existing:
        # Always update name
        existing.name = product.name
        # Update other fields only if incoming value is not None
        for field in ("image_url", "card_number", "product_type", "rarity",
                      "release_date", "category", "group_name", "url"):
            incoming = getattr(product, field)
            if incoming is not None:
                setattr(existing, field, incoming)
    else:
        self.session.add(product)
    self.session.commit()
```

This ensures:
- Multiple scrapers can contribute different fields to the same product
- A scraper that doesn't know the image_url won't overwrite one set by another scraper
- `product_id` is always set by scrapers (it's the TCGPlayer product ID from the source data)

**Other write methods** use `session.add()` wrapped in a try/except for `IntegrityError` (unique constraint violations are silently ignored, matching the existing `INSERT OR IGNORE` behavior).

---

## 7. FastAPI Application

**File:** `src/pokeassistant/api.py`

```python
from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="PokeAssistant API", version="0.1.0")

# CORS — allow_credentials=False (no auth/cookies for now).
# When auth is added later, switch to True and restrict origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)
```

### Endpoint Definitions

| Method | Path | Response | Query Params |
|--------|------|----------|-------------|
| GET | `/api/health` | `HealthResponse` | — |
| GET | `/api/cards` | `PaginatedResponse[CardSummary]` | `limit`, `offset`, `category`, `search`, `sort_by`, `order` |
| GET | `/api/cards/{id}` | `CardDetail` | — |
| GET | `/api/cards/{id}/price-history` | `PriceHistoryPoint[]` | `period` (1M/3M/6M/1Y/ALL) |
| GET | `/api/products` | `PaginatedResponse[ProductSummary]` | `limit`, `offset`, `search`, `sort_by`, `order` |
| GET | `/api/products/{id}` | `ProductDetail` | — |
| GET | `/api/products/{id}/price-history` | `PriceHistoryPoint[]` | `period` |
| GET | `/api/search` | `SearchResult[]` | `q`, `type` (card/product/all) |
| GET | `/api/trends/{keyword}` | `TrendPoint[]` | — |
| GET | `/api/grading/{product_id}` | `GradingRow[]` | — |
| GET | `/api/population/{product_id}` | `PopulationRow[]` | — |

### Sort Parameters

**`sort_by`** valid values:

| Endpoint | Allowed values | Default |
|----------|---------------|---------|
| `/api/cards` | `market_price`, `name`, `change` | `market_price` |
| `/api/products` | `market_price`, `name`, `change`, `release_date` | `market_price` |

**`order`**: `asc` or `desc` (default: `desc`)

Invalid `sort_by` values return 422.

### Category Filter — Current Limitation

The `category` param on `/api/cards` filters by the raw TCGPlayer category string (e.g., `"Pokemon Single"`). The frontend's filter pills ("Pokemon", "English", "Japanese") represent language/game filters that **do not have a backend equivalent yet**. For now:
- `category=null` (default) returns all cards
- The frontend pills should be non-functional or filter client-side until a `language` column is added to the schema (see [Future Backlog](#future-backlog))

### Health Endpoint

```python
@app.get("/api/health")
def health_check(session: Session = Depends(get_db)):
    try:
        session.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception:
        return {"status": "degraded", "db": "disconnected"}
```

### Trend Data — Product Linkage

`GET /api/trends/{keyword}` is keyword-based (matching Google Trends' data model). There is currently **no product_id → keyword mapping** — the frontend must know which keyword to request for a given card. Convention: use the card's product name as the keyword (e.g., `"umbreon ex prismatic evolutions"`). A formal mapping table is deferred to the backlog.

### Error Handling
- 404 for missing products/cards
- 422 for invalid query params (FastAPI default)
- All monetary values returned as **cents** (integers) — frontend converts to dollars

### Server Entrypoint

```python
def run_server():
    """Entry point for `pokeassistant-api` script."""
    import uvicorn
    uvicorn.run("pokeassistant.api:app", host="0.0.0.0", port=8000, reload=True)
```

---

## 8. CLI + Scraper Updates

### CLI (`cli.py`)
- Replace direct `db.py` function calls with repository methods
- Replace `get_connection()` with `get_engine()` + session
- Create a `SQLAlchemyRepository(session)` instance and pass it through
- Scraper results flow through the same pipeline, using `repo.upsert_product()` etc.

### Scrapers
- Currently import from `pokeassistant.models` (dataclasses) to construct results
- Update to construct SQLAlchemy model instances instead
- Core scraping logic (HTTP requests, HTML parsing) stays unchanged
- Each scraper returns model instances that the CLI passes to the repository
- Scrapers must set `product_type` on Product instances: determine from the TCGPlayer category string using the classification rules in Section 1

**Scraper compatibility notes:**
- `Product(product_id=1, name="X")` works without passing `created_at` — the SQLAlchemy model has `default=datetime.now` which auto-fills it.
- Scrapers already pass `datetime` objects for timestamps and `date` objects for dates (e.g., `datetime.now()`, `date.fromisoformat(...)`). Since the models now use `DateTime`/`Date` column types instead of `Text`, these are accepted directly — no `.isoformat()` conversion needed.
- Scrapers return *transient* SQLAlchemy instances (not attached to any session). The repository's write methods handle `session.add()`. Do NOT reuse the same model instance across multiple repository calls — create fresh instances each time.

### db.py Removal
- The old `db.py` is **deleted** after migration. All its functions are replaced by the repository.
- **Before deleting:** Run the existing test suite against the old code to establish a regression baseline. Capture the passing test output. Then delete `db.py` and `test_db.py` together.

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

Add dev dependency:
```toml
[project.optional-dependencies]
dev = [
    # ... existing ...
    "httpx>=0.27",    # for FastAPI TestClient
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
├── models.py                # REWRITTEN → SQLAlchemy ORM models + dollars_to_cents helper
├── schemas.py               # NEW → Pydantic response schemas (generic PaginatedResponse)
├── database.py              # NEW → Singleton engine + session factory + reset_engine()
├── repository.py            # NEW → Abstract repository interface with docstrings
├── repositories/
│   ├── __init__.py          # NEW
│   └── sqlalchemy_repo.py   # NEW → SQLAlchemy implementation with explicit upsert
├── api.py                   # NEW → FastAPI app + endpoints + CORS + health check
├── cli.py                   # UPDATED → use repository
├── db.py                    # DELETED (after regression baseline captured)
└── scrapers/                # UPDATED → use new SQLAlchemy models, set product_type
    ├── __init__.py
    ├── tcgplayer.py
    ├── tcgcsv.py
    ├── pricecharting.py
    ├── gemrate.py
    └── trends.py

tests/
├── conftest.py              # UPDATED → SQLAlchemy test fixtures (in-memory DB)
├── test_models.py           # UPDATED → SQLAlchemy model tests
├── test_repository.py       # NEW → replaces test_db.py
├── test_api.py              # NEW → FastAPI endpoint tests (TestClient + httpx)
├── test_cli.py              # UPDATED
├── test_db.py               # DELETED (after test_repository.py covers all cases)
└── ... (scraper tests — update model construction, minimal logic changes)
```

---

## 11. Testing Strategy

- **Regression baseline first**: Run `pytest` against the current codebase and capture results before any changes.
- **test_repository.py**: Uses in-memory SQLite (`sqlite:///:memory:`) via `reset_engine()` + custom engine injection. Tests all repository methods including upsert merge semantics, unique constraint ignore behavior, sort/filter/pagination, and computed field calculations.
- **test_api.py**: Uses FastAPI `TestClient` (via `httpx`) with an in-memory DB. Tests all endpoints: happy path, 404s, empty data, pagination, sort params, invalid sort_by (422), health check.
- **test_models.py**: Update expectations for SQLAlchemy behavior. Key change: `Product(product_id=1, name="Test").created_at` is no longer auto-set at construction time — the `default=datetime.now` only fires when SQLAlchemy flushes to the DB. Tests that check `created_at is not None` on an unflushed instance need to either flush first or test after insert.
- **Scraper tests**: Remain mostly fixture-based; update model construction from dataclass to SQLAlchemy. Core scraping logic tests unchanged.
- **test_cli.py**: Update to mock the repository instead of raw db functions.

---

## Future Backlog

Items deferred from this spec, to be addressed in future iterations:

### Data Gaps (Frontend needs, backend doesn't have)
- [ ] **Language/game filter** — Add `language` column to `products` ("English", "Japanese", etc.) to support the frontend's filter pills. Currently the pills have no backend equivalent.
- [ ] **Product subtype** — Finer classification beyond "card"/"sealed" (e.g., "booster_box", "etb", "tin", "bundle", "code_card"). Needed for accurate EV calculations.
- [ ] **Cards inside a product** — `product_contents` junction table linking sealed products to the cards they contain. Required for "Cards You Can Open" in ProductDetail.
- [ ] **Pull rates / pull odds** — Editorial/community data per card per set. Needs a data source or manual entry system.
- [ ] **Expected Value (EV)** — Requires product_contents + pull rates + market prices.
- [ ] **Market Sentiment** — Reddit, Twitter/X, eBay velocity, YouTube scraping. Major feature requiring new scrapers + NLP.
- [ ] **Collection / Portfolio tracking** — Needs `user_collections` table, potentially auth system.
- [ ] **Rip vs Flip analysis** — Depends on EV calculation + sealed product price tracking.
- [ ] **Buy Signal analysis** — Composite score from price momentum, sentiment, volume.
- [ ] **Gradeability indicators** — Analysis of centering, surface quality signals.
- [ ] **Active marketplace listings** — Real-time listing feed from TCGPlayer/eBay.
- [ ] **Trend → Product mapping** — Either FK on `trend_data`, a mapping table, or a convention-based lookup so card detail views can auto-fetch relevant trend data.

### Infrastructure
- [ ] **Supabase/Postgres migration** — Write a `SupabaseRepository` implementing `CardRepository`. SQLAlchemy makes this near-trivial (change connection string).
- [ ] **Alembic migrations** — Set up proper schema migration tooling for when the DB has real data.
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
