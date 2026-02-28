from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from pokeassistant.scrapers.pricecharting import (
    build_search_url,
    parse_graded_prices,
    search_card,
    fetch_graded_prices,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


def _mock_html_response(html: str) -> MagicMock:
    mock = MagicMock()
    mock.status_code = 200
    mock.text = html
    mock.url = "https://www.pricecharting.com/game/pokemon-prismatic-evolutions/umbreon-ex-161"
    mock.raise_for_status.return_value = None
    return mock


class TestBuildSearchUrl:
    def test_basic_query(self):
        url = build_search_url("umbreon ex 161")
        assert "search-products" in url
        assert "q=umbreon+ex+161" in url or "q=umbreon%20ex%20161" in url

    def test_includes_type_prices(self):
        url = build_search_url("test")
        assert "type=prices" in url


class TestParseGradedPrices:
    def test_parse_full_prices_table(self):
        html = _load_fixture("pricecharting_card.html")
        gp = parse_graded_prices(
            html,
            product_id=610516,
            url="https://www.pricecharting.com/game/pokemon-prismatic-evolutions/umbreon-ex-161",
        )
        assert gp.product_id == 610516
        assert gp.card_name == "Umbreon ex #161"
        assert gp.source == "pricecharting"
        assert gp.ungraded_cents == 2500
        assert gp.grade_7_cents == 5000
        assert gp.grade_8_cents == 7500
        assert gp.grade_9_cents == 15000
        assert gp.grade_9_5_cents == 25000
        assert gp.psa_10_cents == 417717
        assert gp.bgs_10_cents == 500000
        assert gp.cgc_10_cents == 350000
        assert gp.sgc_10_cents == 200000
        assert gp.pricecharting_url == (
            "https://www.pricecharting.com/game/pokemon-prismatic-evolutions/umbreon-ex-161"
        )

    def test_parse_missing_prices_returns_none(self):
        html = """
        <html><body>
        <div id="product_name">Test Card</div>
        <table id="full-prices"><thead><tr><th>Grade</th><th>Price</th></tr></thead>
        <tbody>
        <tr><td>PSA 10</td><td class="price js-price">N/A</td></tr>
        </tbody></table>
        </body></html>
        """
        gp = parse_graded_prices(html, product_id=1, url="http://example.com")
        assert gp.psa_10_cents is None
        assert gp.ungraded_cents is None


class TestSearchCard:
    @patch("pokeassistant.scrapers.pricecharting.requests.get")
    def test_search_returns_url_on_redirect(self, mock_get):
        """When PriceCharting redirects to a card page, return that URL."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://www.pricecharting.com/game/pokemon-prismatic-evolutions/umbreon-ex-161"
        mock_resp.text = '<div id="product_name">Umbreon ex #161</div>'
        mock_resp.raise_for_status.return_value = None
        # Simulate a redirect (final URL is a card page, not search results)
        mock_resp.history = [MagicMock(status_code=302)]
        mock_get.return_value = mock_resp

        url = search_card("umbreon ex 161 prismatic evolutions")
        assert url == "https://www.pricecharting.com/game/pokemon-prismatic-evolutions/umbreon-ex-161"

    @patch("pokeassistant.scrapers.pricecharting.requests.get")
    def test_search_returns_first_result(self, mock_get):
        """When search shows results page, parse first link."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://www.pricecharting.com/search-products?q=umbreon"
        mock_resp.text = """
        <html><body>
        <table id="games_table">
        <tr class="product">
          <td class="title"><a href="/game/pokemon-prismatic-evolutions/umbreon-ex-161">Umbreon ex #161</a></td>
        </tr>
        </table>
        </body></html>
        """
        mock_resp.history = []
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        url = search_card("umbreon")
        assert url == "https://www.pricecharting.com/game/pokemon-prismatic-evolutions/umbreon-ex-161"

    @patch("pokeassistant.scrapers.pricecharting.requests.get")
    def test_search_no_results(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://www.pricecharting.com/search-products?q=zzznotfound"
        mock_resp.text = "<html><body><p>No results found</p></body></html>"
        mock_resp.history = []
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        url = search_card("zzznotfound")
        assert url is None


class TestFetchGradedPrices:
    @patch("pokeassistant.scrapers.pricecharting.requests.get")
    def test_end_to_end(self, mock_get):
        html = _load_fixture("pricecharting_card.html")
        # First call = search (redirects to card page)
        search_resp = _mock_html_response(html)
        search_resp.history = [MagicMock(status_code=302)]
        # Second call = fetch card page
        card_resp = _mock_html_response(html)
        mock_get.side_effect = [search_resp, card_resp]

        gp = fetch_graded_prices("umbreon ex 161 prismatic evolutions", product_id=610516)
        assert gp is not None
        assert gp.psa_10_cents == 417717
        assert gp.product_id == 610516

    @patch("pokeassistant.scrapers.pricecharting.requests.get")
    def test_returns_none_when_not_found(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://www.pricecharting.com/search-products?q=zzznotfound"
        mock_resp.text = "<html><body><p>No results found</p></body></html>"
        mock_resp.history = []
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        gp = fetch_graded_prices("zzznotfound", product_id=1)
        assert gp is None
