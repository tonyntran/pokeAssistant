from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional


def dollars_to_cents(value) -> Optional[int]:
    """Convert a dollar amount to cents (integer).

    Accepts float, int, string, or None. Returns None if input is None.
    Rounds to nearest cent to avoid floating point issues.
    """
    if value is None:
        return None
    return round(float(value) * 100)


@dataclass
class Product:
    product_id: int
    name: str
    category: Optional[str] = None
    group_name: Optional[str] = None
    url: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PriceSnapshot:
    product_id: int
    timestamp: datetime
    source: str
    low_price_cents: Optional[int] = None
    market_price_cents: Optional[int] = None
    high_price_cents: Optional[int] = None
    listing_count: Optional[int] = None


@dataclass
class SaleRecord:
    product_id: int
    sale_date: date
    price_cents: int
    source: str
    condition: Optional[str] = None
    variant: Optional[str] = None
    quantity: int = 1


@dataclass
class TrendDataPoint:
    keyword: str
    date: date
    interest: int
    source: str


@dataclass
class GradedPrice:
    product_id: int
    card_name: str
    source: str
    timestamp: datetime
    ungraded_cents: Optional[int] = None
    grade_7_cents: Optional[int] = None
    grade_8_cents: Optional[int] = None
    grade_9_cents: Optional[int] = None
    grade_9_5_cents: Optional[int] = None
    psa_10_cents: Optional[int] = None
    bgs_10_cents: Optional[int] = None
    cgc_10_cents: Optional[int] = None
    sgc_10_cents: Optional[int] = None
    pricecharting_url: Optional[str] = None


@dataclass
class PopulationReport:
    card_name: str
    gemrate_id: str
    source: str
    timestamp: datetime
    total_population: int
    psa_10: Optional[int] = None
    psa_9: Optional[int] = None
    psa_8: Optional[int] = None
    bgs_10: Optional[int] = None
    bgs_9_5: Optional[int] = None
    cgc_10: Optional[int] = None
    cgc_9_5: Optional[int] = None
    gem_rate: Optional[float] = None
