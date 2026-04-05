"""Unit tests for CardScanner — runs in CI. All heavy dependencies are mocked."""
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pytest
from PIL import Image

from cardvision.result import CardRecord, OCRExtract, ScanResult
from cardvision.scanner import CardScanner, OCR_CONFIDENCE_THRESHOLD, EMBEDDING_WARN_THRESHOLD
from cardvision.exceptions import IndexNotBuiltError


CHARIZARD = CardRecord(card_id="1", name="Charizard", set_name="Base Set", image_url="", metadata={"card_number": "4/102"})
SHADOWLESS = CardRecord(card_id="2", name="Charizard", set_name="Base Set Shadowless", image_url="", metadata={"card_number": "4/102"})
PIKACHU = CardRecord(card_id="3", name="Pikachu", set_name="Base Set", image_url="", metadata={"card_number": "58/102"})
FAKE_EMBEDDING = np.ones(384, dtype=np.float32) / np.sqrt(384)


@pytest.fixture
def mock_adapter():
    adapter = MagicMock()
    adapter.game_id = "pokemon"
    adapter.get_index_paths.return_value = (Path("/tmp/fake.index"), Path("/tmp/fake.json"))
    return adapter


def make_scanner(mock_adapter):
    """Build a CardScanner with all heavy dependencies replaced by mocks."""
    mock_index = MagicMock()
    mock_index.is_loaded = True
    mock_embedder = MagicMock()
    mock_embedder.embed.return_value = FAKE_EMBEDDING
    mock_detector = MagicMock()
    mock_detector.detect_and_warp.return_value = Image.new("RGB", (400, 560))
    mock_ocr = MagicMock()

    with patch("cardvision.scanner.CardIndex", return_value=mock_index), \
         patch("cardvision.scanner.CardEmbedder", return_value=mock_embedder), \
         patch("cardvision.scanner.CardDetector", return_value=mock_detector), \
         patch("cardvision.scanner.CardOCR", return_value=mock_ocr):
        scanner = CardScanner(mock_adapter)
        scanner._index = mock_index
        scanner._embedder = mock_embedder
        scanner._detector = mock_detector
        scanner._ocr = mock_ocr

    return scanner


def test_ocr_path_used_when_high_confidence(mock_adapter, tmp_path):
    """Path 1: OCR succeeds with confidence >= threshold and single lookup match."""
    scanner = make_scanner(mock_adapter)
    scanner._ocr.extract.return_value = OCRExtract(
        name="Charizard", set_number="4/102", confidence=0.95
    )
    mock_adapter.lookup_by_text.return_value = [CHARIZARD]

    img = tmp_path / "card.jpg"
    Image.new("RGB", (400, 560)).save(img)
    result = scanner.scan(img)

    assert result.top.method == "ocr"
    assert result.top.card.card_id == "1"
    assert result.top.confidence == 0.95
    scanner._embedder.embed.assert_not_called()


def test_falls_through_to_embedding_when_ocr_low_confidence(mock_adapter, tmp_path):
    """Path 2: OCR confidence < OCR_CONFIDENCE_THRESHOLD triggers embedding fallback."""
    scanner = make_scanner(mock_adapter)
    scanner._ocr.extract.return_value = OCRExtract(
        name="Charizard", set_number="4/102", confidence=0.5  # below threshold
    )
    scanner._index.query.return_value = [(CHARIZARD, 0.92)]

    img = tmp_path / "card.jpg"
    Image.new("RGB", (400, 560)).save(img)
    result = scanner.scan(img)

    assert result.top.method == "embedding"
    scanner._embedder.embed.assert_called_once()
    mock_adapter.lookup_by_text.assert_not_called()


def test_falls_through_to_embedding_when_ocr_ambiguous(mock_adapter, tmp_path):
    """Path 3: lookup_by_text returns 2+ results (Shadowless vs Unlimited) → embedding."""
    scanner = make_scanner(mock_adapter)
    scanner._ocr.extract.return_value = OCRExtract(
        name="Charizard", set_number="4/102", confidence=0.95
    )
    mock_adapter.lookup_by_text.return_value = [CHARIZARD, SHADOWLESS]  # ambiguous
    scanner._index.query.return_value = [(CHARIZARD, 0.88), (SHADOWLESS, 0.81)]

    img = tmp_path / "card.jpg"
    Image.new("RGB", (400, 560)).save(img)
    result = scanner.scan(img)

    assert result.top.method == "embedding"
    assert len(result.alternatives) == 1


def test_falls_through_to_embedding_when_ocr_returns_none(mock_adapter, tmp_path):
    """Path 4: OCR extracts nothing (foil/blur) → silent fallback to embedding."""
    scanner = make_scanner(mock_adapter)
    scanner._ocr.extract.return_value = OCRExtract(name=None, set_number=None, confidence=0.0)
    scanner._index.query.return_value = [(PIKACHU, 0.91)]

    img = tmp_path / "card.jpg"
    Image.new("RGB", (400, 560)).save(img)
    result = scanner.scan(img)

    assert result.top.method == "embedding"
    assert result.top.card.card_id == "3"
    mock_adapter.lookup_by_text.assert_not_called()


def test_low_embedding_confidence_result_still_returned(mock_adapter, tmp_path):
    """Path 5: low embedding confidence → ScanResult returned; CLI checks threshold."""
    scanner = make_scanner(mock_adapter)
    scanner._ocr.extract.return_value = OCRExtract(name=None, set_number=None, confidence=0.0)
    low_conf = EMBEDDING_WARN_THRESHOLD - 0.1
    scanner._index.query.return_value = [(CHARIZARD, low_conf)]

    img = tmp_path / "card.jpg"
    Image.new("RGB", (400, 560)).save(img)
    result = scanner.scan(img)

    assert isinstance(result, ScanResult)
    assert result.top.confidence < EMBEDDING_WARN_THRESHOLD


def test_scan_result_has_scan_ms(mock_adapter, tmp_path):
    scanner = make_scanner(mock_adapter)
    scanner._ocr.extract.return_value = OCRExtract(name=None, set_number=None, confidence=0.0)
    scanner._index.query.return_value = [(CHARIZARD, 0.90)]

    img = tmp_path / "card.jpg"
    Image.new("RGB", (400, 560)).save(img)
    result = scanner.scan(img)

    assert result.scan_ms >= 0
