import sys
from unittest.mock import patch, MagicMock

import pytest

from pokeassistant.cli import parse_args, main


class TestParseArgs:
    def test_product_id_required(self):
        with pytest.raises(SystemExit):
            parse_args([])

    def test_product_id(self):
        args = parse_args(["--product-id", "593355"])
        assert args.product_id == 593355

    def test_all_flag(self):
        args = parse_args(["--product-id", "593355", "--all"])
        assert args.all is True

    def test_scrape_flag(self):
        args = parse_args(["--product-id", "593355", "--scrape"])
        assert args.scrape is True

    def test_tcgcsv_flag(self):
        args = parse_args(["--product-id", "593355", "--tcgcsv"])
        assert args.tcgcsv is True

    def test_trends_flag(self):
        args = parse_args(["--product-id", "593355", "--trends"])
        assert args.trends is True

    def test_no_headless_flag(self):
        args = parse_args(["--product-id", "593355", "--no-headless"])
        assert args.no_headless is True

    def test_group_id_optional(self):
        args = parse_args(["--product-id", "593355", "--group-id", "23821"])
        assert args.group_id == 23821

    def test_group_id_defaults_none(self):
        args = parse_args(["--product-id", "593355"])
        assert args.group_id is None

    def test_multiple_flags(self):
        args = parse_args(["--product-id", "593355", "--tcgcsv", "--trends"])
        assert args.tcgcsv is True
        assert args.trends is True
        assert args.scrape is False
        assert args.all is False

    def test_keyword_flag(self):
        args = parse_args([
            "--product-id", "593355",
            "--trends",
            "--keyword", "prismatic evolutions",
            "--keyword", "prismatic evolutions ETB",
        ])
        assert args.keyword == ["prismatic evolutions", "prismatic evolutions ETB"]

    def test_pricecharting_flag(self):
        args = parse_args(["--product-id", "610516", "--pricecharting", "--card-name", "umbreon ex 161"])
        assert args.pricecharting is True
        assert args.card_name == "umbreon ex 161"

    def test_gemrate_flag(self):
        args = parse_args(["--product-id", "610516", "--gemrate", "--card-name", "umbreon ex 161"])
        assert args.gemrate is True

    def test_card_name_defaults_none(self):
        args = parse_args(["--product-id", "593355"])
        assert args.card_name is None

    def test_all_flag_includes_new_sources(self):
        args = parse_args(["--product-id", "593355", "--all"])
        assert args.all is True


class TestMainNoSource:
    def test_no_source_prints_error(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--product-id", "593355"])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "specify at least one" in captured.err.lower()

    def test_pricecharting_requires_card_name(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--product-id", "610516", "--pricecharting"])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--card-name" in captured.err

    def test_gemrate_requires_card_name(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["--product-id", "610516", "--gemrate"])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--card-name" in captured.err
