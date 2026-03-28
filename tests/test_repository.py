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
