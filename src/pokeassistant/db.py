import sqlite3
from pathlib import Path
from typing import Optional

from pokeassistant.models import (
    Product,
    PriceSnapshot,
    SaleRecord,
    TrendDataPoint,
    GradedPrice,
    PopulationReport,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    group_name TEXT,
    url TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS price_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    source TEXT NOT NULL,
    low_price_cents INTEGER,
    market_price_cents INTEGER,
    high_price_cents INTEGER,
    listing_count INTEGER,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    UNIQUE(product_id, timestamp, source)
);

CREATE TABLE IF NOT EXISTS sale_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    sale_date TEXT NOT NULL,
    condition TEXT,
    variant TEXT,
    price_cents INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    source TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    UNIQUE(product_id, sale_date, condition, variant, price_cents)
);

CREATE TABLE IF NOT EXISTS trend_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    date TEXT NOT NULL,
    interest INTEGER NOT NULL,
    source TEXT NOT NULL,
    UNIQUE(keyword, date)
);

CREATE TABLE IF NOT EXISTS graded_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    card_name TEXT NOT NULL,
    source TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    ungraded_cents INTEGER,
    grade_7_cents INTEGER,
    grade_8_cents INTEGER,
    grade_9_cents INTEGER,
    grade_9_5_cents INTEGER,
    psa_10_cents INTEGER,
    bgs_10_cents INTEGER,
    cgc_10_cents INTEGER,
    sgc_10_cents INTEGER,
    pricecharting_url TEXT,
    UNIQUE(card_name, timestamp, source)
);

CREATE TABLE IF NOT EXISTS population_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_name TEXT NOT NULL,
    gemrate_id TEXT NOT NULL,
    source TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    total_population INTEGER NOT NULL,
    psa_10 INTEGER,
    psa_9 INTEGER,
    psa_8 INTEGER,
    bgs_10 INTEGER,
    bgs_9_5 INTEGER,
    cgc_10 INTEGER,
    cgc_9_5 INTEGER,
    gem_rate REAL,
    UNIQUE(gemrate_id, timestamp)
);
"""


def init_db(conn: sqlite3.Connection) -> None:
    """Initialize the database schema."""
    conn.executescript(SCHEMA)
    conn.commit()


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Create a database connection with row factory enabled."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)
    return conn


# --- Product ---

def insert_product(conn: sqlite3.Connection, product: Product) -> None:
    conn.execute(
        """INSERT INTO products (product_id, name, category, group_name, url, created_at)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(product_id) DO UPDATE SET
               name=excluded.name,
               category=COALESCE(excluded.category, products.category),
               group_name=COALESCE(excluded.group_name, products.group_name),
               url=COALESCE(excluded.url, products.url)
        """,
        (
            product.product_id,
            product.name,
            product.category,
            product.group_name,
            product.url,
            product.created_at.isoformat(),
        ),
    )
    conn.commit()


def get_product(conn: sqlite3.Connection, product_id: int) -> Optional[sqlite3.Row]:
    cursor = conn.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
    return cursor.fetchone()


# --- Price Snapshots ---

def insert_price_snapshot(conn: sqlite3.Connection, snap: PriceSnapshot) -> None:
    conn.execute(
        """INSERT OR IGNORE INTO price_snapshots
           (product_id, timestamp, source, low_price_cents, market_price_cents,
            high_price_cents, listing_count)
           VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            snap.product_id,
            snap.timestamp.isoformat(),
            snap.source,
            snap.low_price_cents,
            snap.market_price_cents,
            snap.high_price_cents,
            snap.listing_count,
        ),
    )
    conn.commit()


def get_price_snapshots(conn: sqlite3.Connection, product_id: int) -> list[sqlite3.Row]:
    cursor = conn.execute(
        "SELECT * FROM price_snapshots WHERE product_id = ? ORDER BY timestamp",
        (product_id,),
    )
    return cursor.fetchall()


# --- Sale Records ---

def insert_sale_record(conn: sqlite3.Connection, sale: SaleRecord) -> None:
    conn.execute(
        """INSERT OR IGNORE INTO sale_records
           (product_id, sale_date, condition, variant, price_cents, quantity, source)
           VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sale.product_id,
            sale.sale_date.isoformat(),
            sale.condition,
            sale.variant,
            sale.price_cents,
            sale.quantity,
            sale.source,
        ),
    )
    conn.commit()


def get_sale_records(conn: sqlite3.Connection, product_id: int) -> list[sqlite3.Row]:
    cursor = conn.execute(
        "SELECT * FROM sale_records WHERE product_id = ? ORDER BY sale_date",
        (product_id,),
    )
    return cursor.fetchall()


# --- Trend Data ---

def insert_trend_data(conn: sqlite3.Connection, td: TrendDataPoint) -> None:
    conn.execute(
        """INSERT OR IGNORE INTO trend_data (keyword, date, interest, source)
           VALUES (?, ?, ?, ?)
        """,
        (td.keyword, td.date.isoformat(), td.interest, td.source),
    )
    conn.commit()


def get_trend_data(conn: sqlite3.Connection, keyword: str) -> list[sqlite3.Row]:
    cursor = conn.execute(
        "SELECT * FROM trend_data WHERE keyword = ? ORDER BY date",
        (keyword,),
    )
    return cursor.fetchall()


# --- Graded Prices ---

def insert_graded_price(conn: sqlite3.Connection, gp: GradedPrice) -> None:
    conn.execute(
        """INSERT OR IGNORE INTO graded_prices
           (product_id, card_name, source, timestamp, ungraded_cents,
            grade_7_cents, grade_8_cents, grade_9_cents, grade_9_5_cents,
            psa_10_cents, bgs_10_cents, cgc_10_cents, sgc_10_cents,
            pricecharting_url)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            gp.product_id,
            gp.card_name,
            gp.source,
            gp.timestamp.isoformat(),
            gp.ungraded_cents,
            gp.grade_7_cents,
            gp.grade_8_cents,
            gp.grade_9_cents,
            gp.grade_9_5_cents,
            gp.psa_10_cents,
            gp.bgs_10_cents,
            gp.cgc_10_cents,
            gp.sgc_10_cents,
            gp.pricecharting_url,
        ),
    )
    conn.commit()


def get_graded_prices(conn: sqlite3.Connection, card_name: str) -> list[sqlite3.Row]:
    cursor = conn.execute(
        "SELECT * FROM graded_prices WHERE card_name = ? ORDER BY timestamp",
        (card_name,),
    )
    return cursor.fetchall()


# --- Population Reports ---

def insert_population_report(conn: sqlite3.Connection, pr: PopulationReport) -> None:
    conn.execute(
        """INSERT OR IGNORE INTO population_reports
           (card_name, gemrate_id, source, timestamp, total_population,
            psa_10, psa_9, psa_8, bgs_10, bgs_9_5, cgc_10, cgc_9_5, gem_rate)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            pr.card_name,
            pr.gemrate_id,
            pr.source,
            pr.timestamp.isoformat(),
            pr.total_population,
            pr.psa_10,
            pr.psa_9,
            pr.psa_8,
            pr.bgs_10,
            pr.bgs_9_5,
            pr.cgc_10,
            pr.cgc_9_5,
            pr.gem_rate,
        ),
    )
    conn.commit()


def get_population_reports(conn: sqlite3.Connection, gemrate_id: str) -> list[sqlite3.Row]:
    cursor = conn.execute(
        "SELECT * FROM population_reports WHERE gemrate_id = ? ORDER BY timestamp",
        (gemrate_id,),
    )
    return cursor.fetchall()
