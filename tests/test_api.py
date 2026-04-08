"""Tests for FastAPI endpoints."""

from datetime import datetime, date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from pokeassistant.models import (
    Base, Product, PriceSnapshot, GradedPrice, PopulationReport, TrendDataPoint,
)
from pokeassistant.repositories.sqlalchemy_repo import SQLAlchemyRepository
from pokeassistant.database import get_db
from pokeassistant.api import app, get_repo


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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
