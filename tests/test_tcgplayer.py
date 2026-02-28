import json
from datetime import date, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pokeassistant.scrapers.tcgplayer import (
    parse_price_history,
    parse_product_details,
    parse_listings_count,
    parse_market_price,
    build_snapshot_from_details,
    build_sale_records_from_history,
)
from pokeassistant.models import PriceSnapshot, SaleRecord, Product

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


class TestParseProductDetails:
    def test_basic_fields(self):
        data = _load_fixture("tcgplayer_product_details.json")
        product = parse_product_details(data)
        assert isinstance(product, Product)
        assert product.product_id == 593355
        assert product.name == "Prismatic Evolutions Elite Trainer Box"
        assert product.category == "Pokemon"
        assert product.group_name == "SV: Prismatic Evolutions"

    def test_url_built_from_id(self):
        data = _load_fixture("tcgplayer_product_details.json")
        product = parse_product_details(data)
        assert "593355" in product.url


class TestParseListingsCount:
    def test_extracts_total(self):
        data = _load_fixture("tcgplayer_listings.json")
        count = parse_listings_count(data)
        assert count == 55

    def test_empty_results(self):
        data = {"errors": [], "results": []}
        count = parse_listings_count(data)
        assert count == 0


class TestParseMarketPrice:
    def test_parses_prices_to_cents(self):
        data = _load_fixture("tcgplayer_market_price.json")
        result = parse_market_price(data)
        assert result["market_price_cents"] == 17382
        assert result["low_price_cents"] == 15000
        assert result["high_price_cents"] == 18099

    def test_empty_list(self):
        result = parse_market_price([])
        assert result is None


class TestBuildSnapshotFromDetails:
    def test_creates_snapshot_in_cents(self):
        details = _load_fixture("tcgplayer_product_details.json")
        listings = _load_fixture("tcgplayer_listings.json")
        market = _load_fixture("tcgplayer_market_price.json")

        snap = build_snapshot_from_details(details, listings, market)
        assert isinstance(snap, PriceSnapshot)
        assert snap.product_id == 593355
        assert snap.source == "tcgplayer"
        assert snap.market_price_cents == 17382
        assert snap.low_price_cents == 15000
        assert snap.high_price_cents == 18099
        assert snap.listing_count == 55


class TestParsePriceHistory:
    def test_returns_buckets(self):
        data = _load_fixture("tcgplayer_price_history.json")
        buckets = parse_price_history(data)
        assert len(buckets) == 3
        assert buckets[0]["market_price_cents"] == 17309
        assert buckets[0]["quantity_sold"] == 50

    def test_empty_result(self):
        data = {"count": 0, "result": []}
        buckets = parse_price_history(data)
        assert buckets == []


class TestBuildSaleRecordsFromHistory:
    def test_creates_sale_records(self):
        data = _load_fixture("tcgplayer_price_history.json")
        records = build_sale_records_from_history(data, product_id=593355)
        assert len(records) == 3
        assert all(isinstance(r, SaleRecord) for r in records)
        # First bucket
        assert records[0].product_id == 593355
        assert records[0].price_cents == 17309
        assert records[0].quantity == 50
        assert records[0].source == "tcgplayer"
        assert records[0].condition == "Unopened"
