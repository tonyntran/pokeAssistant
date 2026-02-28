from datetime import datetime, date

import pytest

from pokeassistant.models import (
    Product,
    PriceSnapshot,
    SaleRecord,
    TrendDataPoint,
    GradedPrice,
    PopulationReport,
)
from pokeassistant.db import (
    insert_product,
    insert_price_snapshot,
    insert_sale_record,
    insert_trend_data,
    insert_graded_price,
    insert_population_report,
    get_price_snapshots,
    get_sale_records,
    get_trend_data,
    get_graded_prices,
    get_population_reports,
    get_product,
)


class TestSchemaCreation:
    def test_tables_exist(self, mem_db):
        cursor = mem_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row["name"] for row in cursor.fetchall()]
        assert "products" in tables
        assert "price_snapshots" in tables
        assert "sale_records" in tables
        assert "trend_data" in tables
        assert "graded_prices" in tables
        assert "population_reports" in tables


class TestProductCRUD:
    def test_insert_and_get(self, mem_db):
        product = Product(
            product_id=593355,
            name="Prismatic Evolutions ETB",
            category="Pokemon",
            group_name="Prismatic Evolutions",
            url="https://www.tcgplayer.com/product/593355",
        )
        insert_product(mem_db, product)
        result = get_product(mem_db, 593355)
        assert result is not None
        assert result["name"] == "Prismatic Evolutions ETB"
        assert result["category"] == "Pokemon"

    def test_upsert_product(self, mem_db):
        product = Product(product_id=1, name="Original Name")
        insert_product(mem_db, product)

        updated = Product(product_id=1, name="Updated Name", category="Pokemon")
        insert_product(mem_db, updated)

        result = get_product(mem_db, 1)
        assert result["name"] == "Updated Name"

    def test_get_nonexistent(self, mem_db):
        assert get_product(mem_db, 999) is None


class TestPriceSnapshots:
    def test_insert_and_query(self, mem_db):
        insert_product(mem_db, Product(product_id=1, name="Test"))
        snap = PriceSnapshot(
            product_id=1,
            timestamp=datetime(2025, 1, 15, 12, 0, 0),
            source="tcgplayer",
            low_price_cents=6499,
            market_price_cents=7250,
            high_price_cents=8999,
            listing_count=42,
        )
        insert_price_snapshot(mem_db, snap)

        results = get_price_snapshots(mem_db, 1)
        assert len(results) == 1
        assert results[0]["low_price_cents"] == 6499
        assert results[0]["listing_count"] == 42

    def test_dedup_on_unique_constraint(self, mem_db):
        insert_product(mem_db, Product(product_id=1, name="Test"))
        snap = PriceSnapshot(
            product_id=1,
            timestamp=datetime(2025, 1, 15, 12, 0, 0),
            source="tcgplayer",
            low_price_cents=6499,
        )
        insert_price_snapshot(mem_db, snap)
        # Insert same again — should not create duplicate
        insert_price_snapshot(mem_db, snap)

        results = get_price_snapshots(mem_db, 1)
        assert len(results) == 1

    def test_different_sources_not_deduped(self, mem_db):
        insert_product(mem_db, Product(product_id=1, name="Test"))
        ts = datetime(2025, 1, 15, 12, 0, 0)
        insert_price_snapshot(
            mem_db,
            PriceSnapshot(product_id=1, timestamp=ts, source="tcgplayer", low_price_cents=6499),
        )
        insert_price_snapshot(
            mem_db,
            PriceSnapshot(product_id=1, timestamp=ts, source="tcgcsv", low_price_cents=6500),
        )

        results = get_price_snapshots(mem_db, 1)
        assert len(results) == 2


class TestSaleRecords:
    def test_insert_and_query(self, mem_db):
        insert_product(mem_db, Product(product_id=1, name="Test"))
        sale = SaleRecord(
            product_id=1,
            sale_date=date(2025, 1, 15),
            condition="Near Mint",
            variant="Normal",
            price_cents=7500,
            quantity=2,
            source="tcgplayer",
        )
        insert_sale_record(mem_db, sale)

        results = get_sale_records(mem_db, 1)
        assert len(results) == 1
        assert results[0]["price_cents"] == 7500
        assert results[0]["quantity"] == 2

    def test_dedup(self, mem_db):
        insert_product(mem_db, Product(product_id=1, name="Test"))
        sale = SaleRecord(
            product_id=1,
            sale_date=date(2025, 1, 15),
            condition="Near Mint",
            variant="Normal",
            price_cents=7500,
            quantity=1,
            source="tcgplayer",
        )
        insert_sale_record(mem_db, sale)
        insert_sale_record(mem_db, sale)

        results = get_sale_records(mem_db, 1)
        assert len(results) == 1


class TestTrendData:
    def test_insert_and_query(self, mem_db):
        td = TrendDataPoint(
            keyword="prismatic evolutions",
            date=date(2025, 1, 15),
            interest=85,
            source="google_trends",
        )
        insert_trend_data(mem_db, td)

        results = get_trend_data(mem_db, "prismatic evolutions")
        assert len(results) == 1
        assert results[0]["interest"] == 85

    def test_dedup(self, mem_db):
        td = TrendDataPoint(
            keyword="test",
            date=date(2025, 1, 15),
            interest=50,
            source="google_trends",
        )
        insert_trend_data(mem_db, td)
        insert_trend_data(mem_db, td)

        results = get_trend_data(mem_db, "test")
        assert len(results) == 1


class TestGradedPrices:
    def test_insert_and_query(self, mem_db):
        gp = GradedPrice(
            product_id=610516,
            card_name="Umbreon ex #161",
            source="pricecharting",
            timestamp=datetime(2025, 6, 1, 12, 0, 0),
            psa_10_cents=417717,
            grade_9_cents=15000,
        )
        insert_graded_price(mem_db, gp)

        results = get_graded_prices(mem_db, "Umbreon ex #161")
        assert len(results) == 1
        assert results[0]["psa_10_cents"] == 417717
        assert results[0]["grade_9_cents"] == 15000
        assert results[0]["product_id"] == 610516

    def test_dedup(self, mem_db):
        gp = GradedPrice(
            product_id=1,
            card_name="Test Card",
            source="pricecharting",
            timestamp=datetime(2025, 6, 1, 12, 0, 0),
            psa_10_cents=10000,
        )
        insert_graded_price(mem_db, gp)
        insert_graded_price(mem_db, gp)

        results = get_graded_prices(mem_db, "Test Card")
        assert len(results) == 1


class TestPopulationReports:
    def test_insert_and_query(self, mem_db):
        pr = PopulationReport(
            card_name="Umbreon ex SIR 161",
            gemrate_id="abc123",
            source="gemrate",
            timestamp=datetime(2025, 6, 1, 12, 0, 0),
            total_population=16344,
            psa_10=5000,
            psa_9=3000,
            gem_rate=30.6,
        )
        insert_population_report(mem_db, pr)

        results = get_population_reports(mem_db, "abc123")
        assert len(results) == 1
        assert results[0]["total_population"] == 16344
        assert results[0]["psa_10"] == 5000
        assert results[0]["gem_rate"] == 30.6

    def test_dedup(self, mem_db):
        pr = PopulationReport(
            card_name="Test Card",
            gemrate_id="test123",
            source="gemrate",
            timestamp=datetime(2025, 6, 1, 12, 0, 0),
            total_population=100,
        )
        insert_population_report(mem_db, pr)
        insert_population_report(mem_db, pr)

        results = get_population_reports(mem_db, "test123")
        assert len(results) == 1
