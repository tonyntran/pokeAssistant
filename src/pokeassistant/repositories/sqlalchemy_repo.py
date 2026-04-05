"""SQLAlchemy implementation of CardRepository."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select, func, desc, asc
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

# Period string → number of days
_PERIOD_DAYS = {
    "1M": 30,
    "3M": 90,
    "6M": 180,
    "1Y": 365,
}


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

    def _insert_ignore(self, obj: object) -> None:
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

    # --- Read Operations ---

    def _list_by_type(
        self,
        product_type: str,
        limit: int,
        offset: int,
        search: str | None,
        sort_by: str,
        order: str,
        category: str | None = None,
    ) -> tuple[list, int]:
        """Shared logic for list_cards and list_products."""
        query = self.session.query(Product).filter(Product.product_type == product_type)

        if category:
            query = query.filter(Product.category == category)
        if search:
            query = query.filter(Product.name.ilike(f"%{search}%"))

        # Count before pagination
        total = query.count()

        # Sorting
        if sort_by == "name":
            order_col = Product.name
        elif sort_by == "release_date":
            order_col = Product.release_date
        elif sort_by == "market_price":
            # Correlated subquery for latest market price
            order_col = (
                select(PriceSnapshot.market_price_cents)
                .where(PriceSnapshot.product_id == Product.product_id)
                .order_by(PriceSnapshot.timestamp.desc())
                .limit(1)
                .correlate(Product)
                .scalar_subquery()
            )
        else:
            # Fallback (e.g. "change") — sort by name
            order_col = Product.name

        if order == "asc":
            query = query.order_by(asc(order_col))
        else:
            query = query.order_by(desc(order_col))

        products = query.offset(offset).limit(limit).all()
        return products, total

    def list_cards(
        self,
        limit: int = 50,
        offset: int = 0,
        category: str | None = None,
        search: str | None = None,
        sort_by: str = "market_price",
        order: str = "desc",
    ) -> tuple[list, int]:
        return self._list_by_type(
            product_type="card",
            limit=limit,
            offset=offset,
            search=search,
            sort_by=sort_by,
            order=order,
            category=category,
        )

    def get_card(self, product_id: int):
        return self.session.get(Product, product_id)

    def list_products(
        self,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
        sort_by: str = "market_price",
        order: str = "desc",
    ) -> tuple[list, int]:
        return self._list_by_type(
            product_type="sealed",
            limit=limit,
            offset=offset,
            search=search,
            sort_by=sort_by,
            order=order,
        )

    def get_product(self, product_id: int):
        return self.session.get(Product, product_id)

    def get_price_history(self, product_id: int, period: str = "1M") -> list:
        query = (
            self.session.query(PriceSnapshot)
            .filter(PriceSnapshot.product_id == product_id)
        )

        if period != "ALL" and period in _PERIOD_DAYS:
            cutoff = datetime.now() - timedelta(days=_PERIOD_DAYS[period])
            query = query.filter(PriceSnapshot.timestamp >= cutoff)

        return query.order_by(PriceSnapshot.timestamp.asc()).all()

    def get_price_change(self, product_id: int) -> tuple[int | None, float | None]:
        snapshots = (
            self.session.query(PriceSnapshot)
            .filter(PriceSnapshot.product_id == product_id)
            .order_by(PriceSnapshot.timestamp.desc())
            .limit(2)
            .all()
        )

        if len(snapshots) < 2:
            return None, None

        latest = snapshots[0]
        previous = snapshots[1]

        if latest.market_price_cents is None or previous.market_price_cents is None:
            return None, None

        change_cents = latest.market_price_cents - previous.market_price_cents
        if previous.market_price_cents == 0:
            change_pct = None
        else:
            change_pct = round(
                (change_cents / previous.market_price_cents) * 100, 2
            )

        return change_cents, change_pct

    def get_grading(self, product_id: int) -> list:
        return (
            self.session.query(GradedPrice)
            .filter(GradedPrice.product_id == product_id)
            .order_by(GradedPrice.timestamp.desc())
            .all()
        )

    def get_population(self, product_id: int) -> list:
        return (
            self.session.query(PopulationReport)
            .filter(PopulationReport.product_id == product_id)
            .order_by(PopulationReport.timestamp.desc())
            .all()
        )

    def get_trend_data(self, keyword: str) -> list:
        return (
            self.session.query(TrendDataPoint)
            .filter(TrendDataPoint.keyword == keyword)
            .order_by(TrendDataPoint.date.asc())
            .all()
        )

    def search(self, query: str, result_type: str | None = None) -> list:
        q = self.session.query(Product).filter(Product.name.ilike(f"%{query}%"))

        if result_type == "card":
            q = q.filter(Product.product_type == "card")
        elif result_type == "product":
            q = q.filter(Product.product_type == "sealed")

        return q.limit(20).all()

    def list_cards_with_images(self) -> list[Product]:
        """Return all products that have an image_url set.

        Used by PokemonAdapter.get_card_catalog() to build the FAISS index.
        Fetches all matching rows without limit (contrast with search() which has .limit(20)).
        """
        return (
            self.session.query(Product)
            .filter(Product.image_url.isnot(None))
            .all()
        )

    def find_by_name_and_number(self, name: str, card_number: str) -> list[Product]:
        """Find products matching both name (case-insensitive substring) and card_number exactly.

        Used by PokemonAdapter.lookup_by_text() for OCR-based card identification.
        Does NOT use search() — that method has a hardcoded .limit(20) which would
        silently drop results for common names like 'Pikachu' across many sets.

        Note: name matching is a substring search — "Pikachu" will match "Pikachu V",
        "Pikachu ex", etc. The card_number constraint narrows results in practice.
        """
        return (
            self.session.query(Product)
            .filter(
                Product.name.ilike(f"%{name}%"),
                Product.card_number == card_number,
            )
            .all()
        )
