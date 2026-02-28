from datetime import datetime, date

import pytest

from pokeassistant.models import (
    Product,
    PriceSnapshot,
    SaleRecord,
    TrendDataPoint,
    GradedPrice,
    PopulationReport,
    dollars_to_cents,
)


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
        # $10.995 should round to 1100 cents
        assert dollars_to_cents(10.995) == 1100

    def test_string_float(self):
        assert dollars_to_cents("29.99") == 2999

    def test_string_int(self):
        assert dollars_to_cents("10") == 1000


class TestProduct:
    def test_create(self):
        p = Product(
            product_id=593355,
            name="Prismatic Evolutions Elite Trainer Box",
            category="Pokemon",
            group_name="Prismatic Evolutions",
            url="https://www.tcgplayer.com/product/593355",
        )
        assert p.product_id == 593355
        assert p.name == "Prismatic Evolutions Elite Trainer Box"
        assert p.category == "Pokemon"
        assert p.created_at is not None

    def test_defaults(self):
        p = Product(product_id=1, name="Test")
        assert p.category is None
        assert p.group_name is None
        assert p.url is None


class TestPriceSnapshot:
    def test_create_with_cents(self):
        ts = datetime(2025, 1, 15, 12, 0, 0)
        snap = PriceSnapshot(
            product_id=593355,
            timestamp=ts,
            source="tcgplayer",
            low_price_cents=6499,
            market_price_cents=7250,
            high_price_cents=8999,
            listing_count=42,
        )
        assert snap.low_price_cents == 6499
        assert snap.market_price_cents == 7250
        assert snap.listing_count == 42

    def test_optional_fields_default_none(self):
        snap = PriceSnapshot(
            product_id=1,
            timestamp=datetime.now(),
            source="test",
        )
        assert snap.low_price_cents is None
        assert snap.market_price_cents is None
        assert snap.high_price_cents is None
        assert snap.listing_count is None


class TestSaleRecord:
    def test_create(self):
        sale = SaleRecord(
            product_id=593355,
            sale_date=date(2025, 1, 15),
            condition="Near Mint",
            variant="1st Edition",
            price_cents=7500,
            quantity=1,
            source="tcgplayer",
        )
        assert sale.price_cents == 7500
        assert sale.condition == "Near Mint"

    def test_defaults(self):
        sale = SaleRecord(
            product_id=1,
            sale_date=date.today(),
            price_cents=1000,
            source="test",
        )
        assert sale.condition is None
        assert sale.variant is None
        assert sale.quantity == 1


class TestTrendDataPoint:
    def test_create(self):
        td = TrendDataPoint(
            keyword="prismatic evolutions",
            date=date(2025, 1, 15),
            interest=85,
            source="google_trends",
        )
        assert td.interest == 85

    def test_interest_bounds(self):
        # Google Trends interest is 0-100, but we don't enforce at model level
        td = TrendDataPoint(
            keyword="test",
            date=date.today(),
            interest=0,
            source="google_trends",
        )
        assert td.interest == 0


class TestGradedPrice:
    def test_create_full(self):
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
        assert gp.product_id == 610516
        assert gp.psa_10_cents == 417717
        assert gp.source == "pricecharting"

    def test_optional_fields_default_none(self):
        gp = GradedPrice(
            product_id=1,
            card_name="Test Card",
            source="pricecharting",
            timestamp=datetime.now(),
        )
        assert gp.ungraded_cents is None
        assert gp.psa_10_cents is None
        assert gp.bgs_10_cents is None
        assert gp.pricecharting_url is None


class TestPopulationReport:
    def test_create_full(self):
        ts = datetime(2025, 6, 1, 12, 0, 0)
        pr = PopulationReport(
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
        assert pr.total_population == 16344
        assert pr.gem_rate == 30.6
        assert pr.source == "gemrate"

    def test_optional_fields_default_none(self):
        pr = PopulationReport(
            card_name="Test Card",
            gemrate_id="test123",
            source="gemrate",
            timestamp=datetime.now(),
            total_population=100,
        )
        assert pr.psa_10 is None
        assert pr.bgs_10 is None
        assert pr.gem_rate is None
