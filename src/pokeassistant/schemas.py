"""Pydantic response schemas for the FastAPI endpoints."""

from __future__ import annotations

from datetime import datetime, date
from typing import Generic, TypeVar

from pydantic import BaseModel

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


# --- Products ---

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


# --- Price History ---

class PriceHistoryPoint(BaseModel):
    timestamp: datetime
    market_price_cents: int | None = None
    low_price_cents: int | None = None
    high_price_cents: int | None = None


# --- Grading ---

class GradingRow(BaseModel):
    grade: str
    population: int | None = None
    pct: float | None = None
    price_cents: int | None = None
    trend: str | None = None


# --- Population ---

class PopulationRow(BaseModel):
    grade: str
    count: int


# --- Trends ---

class TrendPoint(BaseModel):
    date: date
    interest: int
    keyword: str


# --- Search ---

class SearchResult(BaseModel):
    type: str
    name: str
    sub: str | None = None
    price_cents: int | None = None
    image_url: str | None = None


# --- Health ---

class HealthResponse(BaseModel):
    status: str
    db: str
