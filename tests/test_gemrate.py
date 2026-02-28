import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from pokeassistant.scrapers.gemrate import (
    parse_search_results,
    parse_population,
    fetch_population,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load_json(name: str):
    return json.loads((FIXTURES / name).read_text())


class TestParseSearchResults:
    def test_returns_list(self):
        data = _load_json("gemrate_search.json")
        results = parse_search_results(data)
        assert len(results) == 2
        assert results[0]["gemrate_id"] == "pkmn-sv-prismatic-evolutions-161"
        assert results[0]["total_population"] == 16344

    def test_empty_results(self):
        results = parse_search_results([])
        assert results == []


class TestParsePopulation:
    def test_extracts_psa_counts(self):
        data = _load_json("gemrate_card_details.json")
        pr = parse_population(
            data,
            card_name="Umbreon ex SIR 161",
            gemrate_id="pkmn-sv-prismatic-evolutions-161",
        )
        assert pr.total_population == 16344
        assert pr.psa_10 == 4543
        assert pr.psa_9 == 7609
        assert pr.psa_8 == 1888

    def test_extracts_bgs_counts(self):
        data = _load_json("gemrate_card_details.json")
        pr = parse_population(
            data,
            card_name="Umbreon ex SIR 161",
            gemrate_id="pkmn-sv-prismatic-evolutions-161",
        )
        # BGS 10 = g10b (1) + g10p (34) + g10 (0, not present) = 35
        assert pr.bgs_10 == 35
        # BGS halves is null in fixture, so 9.5 comes from grades.g9_5 via _get_half
        assert pr.bgs_9_5 is None

    def test_extracts_cgc_counts(self):
        data = _load_json("gemrate_card_details.json")
        pr = parse_population(
            data,
            card_name="Umbreon ex SIR 161",
            gemrate_id="pkmn-sv-prismatic-evolutions-161",
        )
        # CGC 10 = g10 (262) + g10pristine (36) + g10perfect (0) = 298
        assert pr.cgc_10 == 298
        # CGC halves is null
        assert pr.cgc_9_5 is None

    def test_gem_rate_converted_to_percent(self):
        data = _load_json("gemrate_card_details.json")
        pr = parse_population(
            data,
            card_name="Umbreon ex SIR 161",
            gemrate_id="pkmn-sv-prismatic-evolutions-161",
        )
        # PSA gem rate 0.3082 -> 30.82%
        assert pr.gem_rate == 30.82

    def test_source_and_metadata(self):
        data = _load_json("gemrate_card_details.json")
        pr = parse_population(
            data,
            card_name="Umbreon ex SIR 161",
            gemrate_id="pkmn-sv-prismatic-evolutions-161",
        )
        assert pr.source == "gemrate"
        assert pr.gemrate_id == "pkmn-sv-prismatic-evolutions-161"
        assert pr.card_name == "Umbreon ex SIR 161"


class TestFetchPopulation:
    @patch("pokeassistant.scrapers.gemrate.requests.Session")
    def test_end_to_end(self, MockSession):
        session = MagicMock()
        MockSession.return_value = session

        # Mock GET /universal-search (token extraction)
        page_resp = MagicMock()
        page_resp.text = 'var token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0";'
        page_resp.raise_for_status.return_value = None

        # Mock POST /universal-search-query (search)
        search_resp = MagicMock()
        search_resp.json.return_value = _load_json("gemrate_search.json")
        search_resp.raise_for_status.return_value = None

        # Mock GET /card-details (card data)
        details_resp = MagicMock()
        details_resp.json.return_value = _load_json("gemrate_card_details.json")
        details_resp.raise_for_status.return_value = None

        session.get.side_effect = [page_resp, details_resp]
        session.post.return_value = search_resp

        pr = fetch_population("Umbreon ex 161 Prismatic")
        assert pr is not None
        assert pr.total_population == 16344
        assert pr.psa_10 == 4543

    @patch("pokeassistant.scrapers.gemrate.requests.Session")
    def test_returns_none_when_no_results(self, MockSession):
        session = MagicMock()
        MockSession.return_value = session

        page_resp = MagicMock()
        page_resp.text = 'var token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0";'
        page_resp.raise_for_status.return_value = None

        search_resp = MagicMock()
        search_resp.json.return_value = []
        search_resp.raise_for_status.return_value = None

        session.get.return_value = page_resp
        session.post.return_value = search_resp

        pr = fetch_population("zzznotfound")
        assert pr is None
