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

    # --- Read Operations (stubs — implemented in Task 7) ---

    def list_cards(self, limit: int = 50, offset: int = 0, category: str | None = None,
                   search: str | None = None, sort_by: str = "market_price",
                   order: str = "desc") -> tuple[list, int]:
        raise NotImplementedError

    def get_card(self, product_id: int):
        raise NotImplementedError

    def get_price_history(self, product_id: int, period: str = "1M") -> list:
        raise NotImplementedError

    def get_price_change(self, product_id: int) -> tuple[int | None, float | None]:
        raise NotImplementedError

    def list_products(self, limit: int = 50, offset: int = 0,
                      search: str | None = None, sort_by: str = "market_price",
                      order: str = "desc") -> tuple[list, int]:
        raise NotImplementedError

    def get_product(self, product_id: int):
        raise NotImplementedError

    def get_grading(self, product_id: int) -> list:
        raise NotImplementedError

    def get_population(self, product_id: int) -> list:
        raise NotImplementedError

    def get_trend_data(self, keyword: str) -> list:
        raise NotImplementedError

    def search(self, query: str, result_type: str | None = None) -> list:
        raise NotImplementedError
