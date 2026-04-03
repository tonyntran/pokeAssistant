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


class TestListCards:
    def test_returns_only_cards(self, repo, session):
        repo.upsert_product(Product(product_id=1, name="Card", product_type="card"))
        repo.upsert_product(Product(product_id=2, name="ETB", product_type="sealed"))
        cards, total = repo.list_cards()
        assert total == 1
        assert cards[0].product_id == 1

    def test_pagination(self, repo):
        for i in range(5):
            repo.upsert_product(Product(product_id=i+1, name=f"Card {i}", product_type="card"))
        cards, total = repo.list_cards(limit=2, offset=0)
        assert len(cards) == 2
        assert total == 5
        cards2, _ = repo.list_cards(limit=2, offset=2)
        assert len(cards2) == 2

    def test_search_filter(self, repo):
        repo.upsert_product(Product(product_id=1, name="Umbreon ex", product_type="card"))
        repo.upsert_product(Product(product_id=2, name="Pikachu ex", product_type="card"))
        cards, total = repo.list_cards(search="umbreon")
        assert total == 1
        assert cards[0].name == "Umbreon ex"

    def test_sort_by_name(self, repo):
        repo.upsert_product(Product(product_id=1, name="Zebra", product_type="card"))
        repo.upsert_product(Product(product_id=2, name="Alpha", product_type="card"))
        cards, _ = repo.list_cards(sort_by="name", order="asc")
        assert cards[0].name == "Alpha"
        assert cards[1].name == "Zebra"

    def test_empty(self, repo):
        cards, total = repo.list_cards()
        assert cards == []
        assert total == 0


class TestGetCard:
    def test_found(self, repo):
        repo.upsert_product(Product(product_id=1, name="Test", product_type="card"))
        assert repo.get_card(1) is not None

    def test_not_found(self, repo):
        assert repo.get_card(999) is None


class TestListProducts:
    def test_returns_only_sealed(self, repo):
        repo.upsert_product(Product(product_id=1, name="Card", product_type="card"))
        repo.upsert_product(Product(product_id=2, name="ETB", product_type="sealed"))
        prods, total = repo.list_products()
        assert total == 1
        assert prods[0].product_id == 2

    def test_sort_by_release_date(self, repo):
        repo.upsert_product(Product(
            product_id=1, name="Old", product_type="sealed",
            release_date=date(2024, 1, 1),
        ))
        repo.upsert_product(Product(
            product_id=2, name="New", product_type="sealed",
            release_date=date(2025, 6, 1),
        ))
        prods, _ = repo.list_products(sort_by="release_date", order="desc")
        assert prods[0].name == "New"


class TestGetProduct:
    def test_found(self, repo):
        repo.upsert_product(Product(product_id=1, name="ETB", product_type="sealed"))
        assert repo.get_product(1) is not None

    def test_not_found(self, repo):
        assert repo.get_product(999) is None


class TestPriceHistory:
    def test_returns_ordered(self, repo):
        repo.upsert_product(Product(product_id=1, name="Test"))
        repo.insert_price_snapshot(PriceSnapshot(
            product_id=1, timestamp=datetime(2025, 3, 1), source="s", market_price_cents=100,
        ))
        repo.insert_price_snapshot(PriceSnapshot(
            product_id=1, timestamp=datetime(2025, 3, 15), source="s", market_price_cents=200,
        ))
        history = repo.get_price_history(1, period="ALL")
        assert len(history) == 2
        assert history[0].timestamp < history[1].timestamp

    def test_period_filter(self, repo):
        repo.upsert_product(Product(product_id=1, name="Test"))
        repo.insert_price_snapshot(PriceSnapshot(
            product_id=1, timestamp=datetime(2020, 1, 1), source="s", market_price_cents=100,
        ))
        repo.insert_price_snapshot(PriceSnapshot(
            product_id=1, timestamp=datetime.now(), source="s2", market_price_cents=200,
        ))
        history = repo.get_price_history(1, period="1M")
        assert len(history) == 1  # Only the recent one


class TestPriceChange:
    def test_computes_change(self, repo):
        repo.upsert_product(Product(product_id=1, name="Test"))
        repo.insert_price_snapshot(PriceSnapshot(
            product_id=1, timestamp=datetime(2025, 3, 1), source="s", market_price_cents=1000,
        ))
        repo.insert_price_snapshot(PriceSnapshot(
            product_id=1, timestamp=datetime(2025, 3, 15), source="s2", market_price_cents=1200,
        ))
        change_cents, change_pct = repo.get_price_change(1)
        assert change_cents == 200
        assert abs(change_pct - 20.0) < 0.01

    def test_no_snapshots(self, repo):
        repo.upsert_product(Product(product_id=1, name="Test"))
        change_cents, change_pct = repo.get_price_change(1)
        assert change_cents is None
        assert change_pct is None

    def test_single_snapshot(self, repo):
        repo.upsert_product(Product(product_id=1, name="Test"))
        repo.insert_price_snapshot(PriceSnapshot(
            product_id=1, timestamp=datetime(2025, 3, 1), source="s", market_price_cents=1000,
        ))
        change_cents, change_pct = repo.get_price_change(1)
        assert change_cents is None
        assert change_pct is None


class TestGetGrading:
    def test_returns_grading(self, repo):
        repo.upsert_product(Product(product_id=1, name="Test"))
        repo.insert_graded_price(GradedPrice(
            product_id=1, card_name="Test", source="pc",
            timestamp=datetime(2025, 6, 1), psa_10_cents=4000,
        ))
        results = repo.get_grading(1)
        assert len(results) == 1


class TestGetPopulation:
    def test_returns_population(self, repo):
        repo.upsert_product(Product(product_id=1, name="Test"))
        repo.insert_population_report(PopulationReport(
            product_id=1, card_name="Test", gemrate_id="x",
            source="gr", timestamp=datetime(2025, 6, 1), total_population=100,
        ))
        results = repo.get_population(1)
        assert len(results) == 1


class TestGetTrendData:
    def test_returns_ordered(self, repo):
        repo.insert_trend_data(TrendDataPoint(
            keyword="test", date=date(2025, 3, 15), interest=80, source="gt",
        ))
        repo.insert_trend_data(TrendDataPoint(
            keyword="test", date=date(2025, 3, 1), interest=50, source="gt",
        ))
        results = repo.get_trend_data("test")
        assert len(results) == 2
        assert results[0].date < results[1].date

    def test_filters_by_keyword(self, repo):
        repo.insert_trend_data(TrendDataPoint(
            keyword="a", date=date(2025, 3, 1), interest=50, source="gt",
        ))
        repo.insert_trend_data(TrendDataPoint(
            keyword="b", date=date(2025, 3, 1), interest=60, source="gt",
        ))
        results = repo.get_trend_data("a")
        assert len(results) == 1


class TestSearch:
    def test_search_cards(self, repo):
        repo.upsert_product(Product(product_id=1, name="Umbreon ex", product_type="card"))
        repo.upsert_product(Product(product_id=2, name="ETB", product_type="sealed"))
        results = repo.search("umbreon", result_type="card")
        assert len(results) == 1
        assert results[0].name == "Umbreon ex"

    def test_search_all(self, repo):
        repo.upsert_product(Product(product_id=1, name="Umbreon ex", product_type="card"))
        repo.upsert_product(Product(product_id=2, name="Umbreon Box", product_type="sealed"))
        results = repo.search("umbreon")
        assert len(results) == 2

    def test_search_empty(self, repo):
        results = repo.search("nonexistent")
        assert results == []


# ---------------------------------------------------------------------------
# Fixtures for find_by_name_and_number tests
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_product(session):
    """A single Charizard 4/102 in the Base Set, committed to the in-memory DB."""
    p = Product(
        product_id=12345,
        name="Charizard",
        card_number="4/102",
        group_name="Base Set",
    )
    session.add(p)
    session.commit()
    return p


# ---------------------------------------------------------------------------
# Tests for find_by_name_and_number
# ---------------------------------------------------------------------------

def test_find_by_name_and_number_returns_exact_match(session, sample_product):
    """find_by_name_and_number returns products matching both name and card_number."""
    repo = SQLAlchemyRepository(session)
    results = repo.find_by_name_and_number("Charizard", "4/102")
    assert len(results) == 1
    assert results[0].name == "Charizard"
    assert results[0].card_number == "4/102"


def test_find_by_name_and_number_returns_empty_when_no_match(session):
    """find_by_name_and_number returns empty list when no card matches."""
    repo = SQLAlchemyRepository(session)
    results = repo.find_by_name_and_number("Nonexistent", "999/999")
    assert results == []


def test_find_by_name_and_number_returns_multiple_when_ambiguous(session):
    """find_by_name_and_number returns all matches for same name+number (e.g. Shadowless)."""
    repo = SQLAlchemyRepository(session)
    # Add two Charizards with the same card_number but different product_ids
    session.add(Product(
        product_id=12345,
        name="Charizard",
        card_number="4/102",
        group_name="Base Set",
    ))
    session.add(Product(
        product_id=99999,
        name="Charizard",
        card_number="4/102",
        group_name="Base Set Shadowless",
    ))
    session.commit()
    results = repo.find_by_name_and_number("Charizard", "4/102")
    assert len(results) == 2
