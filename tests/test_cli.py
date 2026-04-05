import sys
from unittest.mock import patch, MagicMock

import pytest

from pokeassistant.cli import parse_args, main


class TestParseArgs:
    def test_product_id_required(self):
        with pytest.raises(SystemExit):
            parse_args([])

    def test_product_id(self):
        args = parse_args(["track", "--product-id", "593355"])
        assert args.product_id == 593355

    def test_all_flag(self):
        args = parse_args(["track", "--product-id", "593355", "--all"])
        assert args.all is True

    def test_scrape_flag(self):
        args = parse_args(["track", "--product-id", "593355", "--scrape"])
        assert args.scrape is True

    def test_tcgcsv_flag(self):
        args = parse_args(["track", "--product-id", "593355", "--tcgcsv"])
        assert args.tcgcsv is True

    def test_trends_flag(self):
        args = parse_args(["track", "--product-id", "593355", "--trends"])
        assert args.trends is True

    def test_no_headless_flag(self):
        args = parse_args(["track", "--product-id", "593355", "--no-headless"])
        assert args.no_headless is True

    def test_group_id_optional(self):
        args = parse_args(["track", "--product-id", "593355", "--group-id", "23821"])
        assert args.group_id == 23821

    def test_group_id_defaults_none(self):
        args = parse_args(["track", "--product-id", "593355"])
        assert args.group_id is None

    def test_multiple_flags(self):
        args = parse_args(["track", "--product-id", "593355", "--tcgcsv", "--trends"])
        assert args.tcgcsv is True
        assert args.trends is True
        assert args.scrape is False
        assert args.all is False

    def test_keyword_flag(self):
        args = parse_args([
            "track", "--product-id", "593355",
            "--trends",
            "--keyword", "prismatic evolutions",
            "--keyword", "prismatic evolutions ETB",
        ])
        assert args.keyword == ["prismatic evolutions", "prismatic evolutions ETB"]

    def test_pricecharting_flag(self):
        args = parse_args(["track", "--product-id", "610516", "--pricecharting", "--card-name", "umbreon ex 161"])
        assert args.pricecharting is True
        assert args.card_name == "umbreon ex 161"

    def test_gemrate_flag(self):
        args = parse_args(["track", "--product-id", "610516", "--gemrate", "--card-name", "umbreon ex 161"])
        assert args.gemrate is True

    def test_card_name_defaults_none(self):
        args = parse_args(["track", "--product-id", "593355"])
        assert args.card_name is None

    def test_all_flag_includes_new_sources(self):
        args = parse_args(["track", "--product-id", "593355", "--all"])
        assert args.all is True


class TestMainNoSource:
    def test_no_source_prints_error(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["track", "--product-id", "593355"])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "specify at least one" in captured.err.lower()

    def test_pricecharting_requires_card_name(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["track", "--product-id", "610516", "--pricecharting"])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--card-name" in captured.err

    def test_gemrate_requires_card_name(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main(["track", "--product-id", "610516", "--gemrate"])
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "--card-name" in captured.err


class TestScanSubcommand:
    def test_scan_requires_image_or_build_index(self):
        with pytest.raises(SystemExit):
            parse_args(["scan"])

    def test_scan_image_and_build_index_are_mutually_exclusive(self):
        with pytest.raises(SystemExit):
            parse_args(["scan", "--image", "card.jpg", "--build-index"])

    def test_scan_image_parses_path(self):
        args = parse_args(["scan", "--image", "card.jpg"])
        assert args.image == "card.jpg"
        assert args.command == "scan"

    def test_scan_build_index_flag(self):
        args = parse_args(["scan", "--build-index"])
        assert args.build_index is True

    def test_scan_top_default_is_3(self):
        args = parse_args(["scan", "--image", "card.jpg"])
        assert args.top == 3

    def test_scan_top_custom(self):
        args = parse_args(["scan", "--image", "card.jpg", "--top", "5"])
        assert args.top == 5

    def test_track_parses_product_id(self):
        args = parse_args(["track", "--product-id", "3816", "--tcgcsv"])
        assert args.product_id == 3816
        assert args.tcgcsv is True

    def test_track_subcommand_required(self):
        with pytest.raises(SystemExit):
            parse_args(["track"])  # missing --product-id


class TestRunScan:
    def test_scan_build_index_calls_build_index(self, tmp_path):
        """--build-index path calls CardScanner.build_index()."""
        with patch("pokeassistant.cli.CardScanner") as mock_scanner_cls, \
             patch("pokeassistant.cli.PokemonAdapter") as mock_adapter_cls:
            mock_adapter = MagicMock()
            mock_adapter_cls.return_value = mock_adapter
            mock_report = MagicMock()
            mock_report.embedded = 10
            mock_report.total = 10
            mock_report.skipped = 0
            mock_report.duration_seconds = 5.0
            mock_scanner_cls.build_index.return_value = mock_report

            args = parse_args(["scan", "--build-index"])
            from pokeassistant.cli import run_scan
            run_scan(args)

            mock_scanner_cls.build_index.assert_called_once_with(mock_adapter)

    def test_scan_image_calls_scanner_scan(self, tmp_path):
        """--image path creates scanner and calls scan()."""
        img = tmp_path / "card.jpg"
        from PIL import Image
        Image.new("RGB", (400, 560)).save(img)

        mock_card = MagicMock()
        mock_card.name = "Charizard"
        mock_card.set_name = "Base Set"
        mock_card.card_id = "1"
        mock_card.metadata = {"card_number": "4/102"}

        mock_match = MagicMock()
        mock_match.card = mock_card
        mock_match.confidence = 0.95
        mock_match.method = "ocr"

        mock_result = MagicMock()
        mock_result.top = mock_match
        mock_result.alternatives = []
        mock_result.scan_ms = 50.0

        with patch("pokeassistant.cli.CardScanner") as mock_scanner_cls, \
             patch("pokeassistant.cli.PokemonAdapter") as mock_adapter_cls, \
             patch("pokeassistant.cli.Path") as mock_path_cls:
            mock_adapter = MagicMock()
            mock_adapter_cls.return_value = mock_adapter
            mock_adapter.get_index_paths.return_value = (tmp_path / "p.index", tmp_path / "p.json")
            (tmp_path / "p.index").write_bytes(b"")
            (tmp_path / "p.json").write_text("[]")

            mock_scanner = MagicMock()
            mock_scanner_cls.return_value = mock_scanner
            mock_scanner.scan.return_value = mock_result
            mock_path_cls.return_value = img  # Path(args.image) → img

            args = parse_args(["scan", "--image", str(img)])
            from pokeassistant.cli import run_scan
            run_scan(args)

            mock_scanner.scan.assert_called_once()
