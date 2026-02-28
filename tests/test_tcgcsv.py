import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from pokeassistant.scrapers.tcgcsv import (
    fetch_groups,
    fetch_prices,
    fetch_products,
    find_group_by_name,
    get_price_snapshot_for_product,
)
from pokeassistant.models import PriceSnapshot, Product

FIXTURES = Path(__file__).parent / "fixtures"


def _mock_response(fixture_name: str) -> MagicMock:
    """Create a mock requests.Response from a fixture file."""
    data = json.loads((FIXTURES / fixture_name).read_text())
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = data
    mock.raise_for_status.return_value = None
    return mock


class TestFetchGroups:
    @patch("pokeassistant.scrapers.tcgcsv.requests.get")
    def test_returns_group_list(self, mock_get):
        mock_get.return_value = _mock_response("tcgcsv_groups.json")
        groups = fetch_groups()
        assert len(groups) == 3
        assert groups[0]["groupId"] == 23821
        assert groups[0]["name"] == "SV: Prismatic Evolutions"

    @patch("pokeassistant.scrapers.tcgcsv.requests.get")
    def test_find_group_by_name(self, mock_get):
        mock_get.return_value = _mock_response("tcgcsv_groups.json")
        group = find_group_by_name("prismatic")
        assert group is not None
        assert group["groupId"] == 23821

    @patch("pokeassistant.scrapers.tcgcsv.requests.get")
    def test_find_group_no_match(self, mock_get):
        mock_get.return_value = _mock_response("tcgcsv_groups.json")
        group = find_group_by_name("nonexistent set")
        assert group is None


class TestFetchProducts:
    @patch("pokeassistant.scrapers.tcgcsv.requests.get")
    def test_returns_product_list(self, mock_get):
        mock_get.return_value = _mock_response("tcgcsv_products.json")
        products = fetch_products(23821)
        assert len(products) == 2
        assert products[0]["productId"] == 593355

    @patch("pokeassistant.scrapers.tcgcsv.requests.get")
    def test_returns_product_models(self, mock_get):
        mock_get.return_value = _mock_response("tcgcsv_products.json")
        products = fetch_products(23821, as_models=True)
        assert len(products) == 2
        assert isinstance(products[0], Product)
        assert products[0].product_id == 593355
        assert products[0].name == "Prismatic Evolutions Elite Trainer Box"


class TestFetchPrices:
    @patch("pokeassistant.scrapers.tcgcsv.requests.get")
    def test_returns_raw_prices(self, mock_get):
        mock_get.return_value = _mock_response("tcgcsv_prices.json")
        prices = fetch_prices(23821)
        assert len(prices) == 3
        assert prices[0]["productId"] == 593355
        assert prices[0]["lowPrice"] == 170.0

    @patch("pokeassistant.scrapers.tcgcsv.requests.get")
    def test_get_snapshot_for_product(self, mock_get):
        mock_get.return_value = _mock_response("tcgcsv_prices.json")
        snapshot = get_price_snapshot_for_product(23821, 593355)
        assert snapshot is not None
        assert isinstance(snapshot, PriceSnapshot)
        assert snapshot.product_id == 593355
        assert snapshot.source == "tcgcsv"
        # Prices should be in cents
        assert snapshot.low_price_cents == 17000
        assert snapshot.market_price_cents == 17268
        assert snapshot.high_price_cents == 111500

    @patch("pokeassistant.scrapers.tcgcsv.requests.get")
    def test_get_snapshot_not_found(self, mock_get):
        mock_get.return_value = _mock_response("tcgcsv_prices.json")
        snapshot = get_price_snapshot_for_product(23821, 999999)
        assert snapshot is None
