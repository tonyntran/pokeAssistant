from __future__ import annotations

from datetime import datetime, date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from pokeassistant.models import (
    Base,
    Product,
    PriceSnapshot,
    SaleRecord,
    TrendDataPoint,
    GradedPrice,
    PopulationReport,
    dollars_to_cents,
)


@pytest.fixture
def session():
    """In-memory SQLAlchemy session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


# ── dollars_to_cents ──────────────────────────────────────────────────


class TestDollarsToCents:
    def test_whole_dollars(self):
        assert dollars_to_cents(10.0) == 1000

    def test_with_cents(self):
        assert dollars_to_cents(19.99) == 1999

    def test_zero(self):
        assert dollars_to_cents(0.0) == 0

    def test_none_returns_none(self):
        assert dollars_to_cents(None) is None

    def test_negative(self):
        assert dollars_to_cents(-5.50) == -550

    def test_fractional_cent_rounds(self):
        assert dollars_to_cents(10.995) == 1100

    def test_string_float(self):
        assert dollars_to_cents("29.99") == 2999

    def test_string_int(self):
        assert dollars_to_cents("10") == 1000


# ── Product ───────────────────────────────────────────────────────────


class TestProduct:
    def test_create_with_all_fields(self, session: Session):
        p = Product(
            product_id=593355,
            name="Prismatic Evolutions Elite Trainer Box",
            category="Pokemon",
            group_name="Prismatic Evolutions",
            url="https://www.tcgplayer.com/product/593355",
            image_url="https://images.example.com/593355.jpg",
            card_number="284/217",
            product_type="sealed",
            rarity="Special Illustration Rare",
            release_date=date(2025, 1, 17),
        )
        session.add(p)
        session.flush()
        assert p.product_id == 593355
        assert p.name == "Prismatic Evolutions Elite Trainer Box"
        assert p.category == "Pokemon"
        assert p.image_url == "https://images.example.com/593355.jpg"
        assert p.card_number == "284/217"
        assert p.product_type == "sealed"
        assert p.rarity == "Special Illustration Rare"
        assert p.release_date == date(2025, 1, 17)

    def test_created_at_default(self, session: Session):
        """created_at is auto-filled by SQLAlchemy on flush (not at construction)."""
        p = Product(product_id=1, name="Test Card")
        session.add(p)
        session.flush()
        assert p.created_at is not None
        assert isinstance(p.created_at, datetime)

    def test_new_fields_default_none(self, session: Session):
        p = Product(product_id=2, name="Test")
        session.add(p)
        session.flush()
        assert p.image_url is None
        assert p.card_number is None
        assert p.product_type is None
        assert p.rarity is None
        assert p.release_date is None
        assert p.category is None
        assert p.group_name is None
        assert p.url is None

    def test_repr(self):
        p = Product(product_id=1, name="Test Card", product_type="card")
        assert repr(p) == "<Product(id=1, name='Test Card', type='card')>"


# ── PriceSnapshot ────────────────────────────────────────────────────


class TestPriceSnapshot:
    def test_create(self, session: Session):
        session.add(Product(product_id=1, name="P"))
        ts = datetime(2025, 1, 15, 12, 0, 0)
        snap = PriceSnapshot(
            product_id=1,
            timestamp=ts,
            source="tcgplayer",
            low_price_cents=6499,
            market_price_cents=7250,
            high_price_cents=8999,
            listing_count=42,
        )
        session.add(snap)
        session.flush()
        assert snap.id is not None
        assert snap.low_price_cents == 6499
        assert snap.market_price_cents == 7250
        assert snap.high_price_cents == 8999
        assert snap.listing_count == 42

    def test_optional_fields_default_none(self, session: Session):
        session.add(Product(product_id=2, name="P2"))
        snap = PriceSnapshot(
            product_id=2,
            timestamp=datetime.now(),
            source="test",
        )
        session.add(snap)
        session.flush()
        assert snap.low_price_cents is None
        assert snap.market_price_cents is None
        assert snap.high_price_cents is None
        assert snap.listing_count is None

    def test_repr(self):
        ts = datetime(2025, 1, 15, 12, 0, 0)
        snap = PriceSnapshot(product_id=1, timestamp=ts, source="x", market_price_cents=100)
        assert "market=100" in repr(snap)


# ── SaleRecord ───────────────────────────────────────────────────────


class TestSaleRecord:
    def test_create(self, session: Session):
        session.add(Product(product_id=1, name="P"))
        sale = SaleRecord(
            product_id=1,
            sale_date=date(2025, 1, 15),
            condition="Near Mint",
            variant="1st Edition",
            price_cents=7500,
            quantity=1,
            source="tcgplayer",
        )
        session.add(sale)
        session.flush()
        assert sale.id is not None
        assert sale.price_cents == 7500
        assert sale.condition == "Near Mint"

    def test_defaults(self, session: Session):
        session.add(Product(product_id=2, name="P2"))
        sale = SaleRecord(
            product_id=2,
            sale_date=date.today(),
            price_cents=1000,
            source="test",
        )
        session.add(sale)
        session.flush()
        assert sale.condition is None
        assert sale.variant is None
        assert sale.quantity == 1

    def test_repr(self):
        sale = SaleRecord(product_id=1, sale_date=date(2025, 1, 1), price_cents=500, source="x")
        assert "price=500" in repr(sale)


# ── TrendDataPoint ───────────────────────────────────────────────────


class TestTrendDataPoint:
    def test_create(self, session: Session):
        td = TrendDataPoint(
            keyword="prismatic evolutions",
            date=date(2025, 1, 15),
            interest=85,
            source="google_trends",
        )
        session.add(td)
        session.flush()
        assert td.id is not None
        assert td.interest == 85

    def test_interest_zero(self, session: Session):
        td = TrendDataPoint(
            keyword="test",
            date=date.today(),
            interest=0,
            source="google_trends",
        )
        session.add(td)
        session.flush()
        assert td.interest == 0

    def test_repr(self):
        td = TrendDataPoint(keyword="test", date=date(2025, 1, 1), interest=50, source="x")
        assert "keyword='test'" in repr(td)


# ── GradedPrice ──────────────────────────────────────────────────────


class TestGradedPrice:
    def test_create_full(self, session: Session):
        session.add(Product(product_id=610516, name="Umbreon"))
        ts = datetime(2025, 6, 1, 12, 0, 0)
        gp = GradedPrice(
            product_id=610516,
            card_name="Umbreon ex #161",
            source="pricecharting",
            timestamp=ts,
            ungraded_cents=2500,
            grade_7_cents=5000,
            grade_8_cents=7500,
            grade_9_cents=15000,
            grade_9_5_cents=25000,
            psa_10_cents=417717,
            bgs_10_cents=500000,
            cgc_10_cents=350000,
            sgc_10_cents=200000,
            pricecharting_url="https://www.pricecharting.com/game/pokemon-prismatic-evolutions/umbreon-ex-161",
        )
        session.add(gp)
        session.flush()
        assert gp.id is not None
        assert gp.product_id == 610516
        assert gp.psa_10_cents == 417717

    def test_optional_fields_default_none(self, session: Session):
        session.add(Product(product_id=1, name="P"))
        gp = GradedPrice(
            product_id=1,
            card_name="Test Card",
            source="pricecharting",
            timestamp=datetime.now(),
        )
        session.add(gp)
        session.flush()
        assert gp.ungraded_cents is None
        assert gp.psa_10_cents is None
        assert gp.bgs_10_cents is None
        assert gp.pricecharting_url is None

    def test_fk_relationship(self, session: Session):
        prod = Product(product_id=99, name="FK Test")
        session.add(prod)
        gp = GradedPrice(
            product_id=99,
            card_name="FK Card",
            source="pricecharting",
            timestamp=datetime.now(),
        )
        session.add(gp)
        session.flush()
        assert gp.product is prod
        assert gp in prod.graded_prices

    def test_repr(self):
        gp = GradedPrice(
            card_name="Umbreon", source="x", timestamp=datetime.now(), psa_10_cents=100
        )
        assert "card='Umbreon'" in repr(gp)


# ── PopulationReport ────────────────────────────────────────────────


class TestPopulationReport:
    def test_create_full(self, session: Session):
        session.add(Product(product_id=1, name="P"))
        ts = datetime(2025, 6, 1, 12, 0, 0)
        pr = PopulationReport(
            product_id=1,
            card_name="Umbreon ex SIR 161",
            gemrate_id="abc123",
            source="gemrate",
            timestamp=ts,
            total_population=16344,
            psa_10=5000,
            psa_9=3000,
            psa_8=1000,
            bgs_10=200,
            bgs_9_5=500,
            cgc_10=150,
            cgc_9_5=300,
            gem_rate=30.6,
        )
        session.add(pr)
        session.flush()
        assert pr.id is not None
        assert pr.total_population == 16344
        assert pr.gem_rate == 30.6

    def test_optional_fields_default_none(self, session: Session):
        session.add(Product(product_id=2, name="P2"))
        pr = PopulationReport(
            product_id=2,
            card_name="Test Card",
            gemrate_id="test123",
            source="gemrate",
            timestamp=datetime.now(),
            total_population=100,
        )
        session.add(pr)
        session.flush()
        assert pr.psa_10 is None
        assert pr.bgs_10 is None
        assert pr.gem_rate is None

    def test_fk_relationship(self, session: Session):
        prod = Product(product_id=50, name="Pop Test")
        session.add(prod)
        pr = PopulationReport(
            product_id=50,
            card_name="Pop Card",
            gemrate_id="pop1",
            source="gemrate",
            timestamp=datetime.now(),
            total_population=500,
        )
        session.add(pr)
        session.flush()
        assert pr.product is prod
        assert pr in prod.population_reports

    def test_repr(self):
        pr = PopulationReport(
            card_name="Umbreon", gemrate_id="x", source="x",
            timestamp=datetime.now(), total_population=100,
        )
        assert "card='Umbreon'" in repr(pr)
        assert "total=100" in repr(pr)
