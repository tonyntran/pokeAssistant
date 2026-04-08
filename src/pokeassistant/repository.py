"""Abstract repository interface for data access.

Implementations: SQLAlchemyRepository (current), SupabaseRepository (future).
"""

from __future__ import annotations

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
