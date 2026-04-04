"""Tests for CardOCR.

Unit tests (regex) run without any model download.
Integration tests require EasyOCR model download (~150MB):
    pytest tests/test_cardvision/test_ocr.py -m integration -v
"""
import pytest
from PIL import Image, ImageDraw, ImageFont

from cardvision.ocr import CardOCR, _SET_NUMBER_RE
from cardvision.result import OCRExtract
from cardvision.detector import CardDetector


# ---------------------------------------------------------------------------
# Unit tests — no EasyOCR, no model download
# ---------------------------------------------------------------------------

def test_set_number_regex_matches_standard_formats():
    assert _SET_NUMBER_RE.fullmatch("4/102")
    assert _SET_NUMBER_RE.fullmatch("025/198")
    assert _SET_NUMBER_RE.fullmatch("SV001/SV122")
    assert _SET_NUMBER_RE.fullmatch("TG01/TG30")


def test_set_number_regex_rejects_noise():
    assert not _SET_NUMBER_RE.fullmatch("Pikachu")
    assert not _SET_NUMBER_RE.fullmatch("1995/2023")   # copyright year — too many digits
    assert not _SET_NUMBER_RE.fullmatch("HP120")


@pytest.mark.integration
def test_extract_returns_ocr_extract_type(tmp_path):
    card = Image.new("RGB", (400, 560), color=(255, 255, 255))
    ocr = CardOCR()
    result = ocr.extract(card)
    assert isinstance(result, OCRExtract)


@pytest.mark.integration
def test_extract_on_blank_card_returns_none_fields():
    """A featureless white card should produce no confident OCR output."""
    card = Image.new("RGB", (400, 560), color=(255, 255, 255))
    ocr = CardOCR()
    result = ocr.extract(card)
    # Blank image should yield nothing meaningful
    assert result.name is None or len(result.name.strip()) == 0


@pytest.mark.integration
def test_extract_confidence_is_between_0_and_1():
    card = Image.new("RGB", (400, 560), color=(200, 200, 200))
    ocr = CardOCR()
    result = ocr.extract(card)
    assert 0.0 <= result.confidence <= 1.0


@pytest.mark.integration
def test_extract_on_blurry_card_falls_through():
    """Heavily blurred card should not produce high-confidence OCR."""
    import PIL.ImageFilter
    card = Image.new("RGB", (400, 560), color=(220, 220, 220))
    blurry = card.filter(PIL.ImageFilter.GaussianBlur(radius=10))
    ocr = CardOCR()
    result = ocr.extract(blurry)
    # Either name is None/empty or confidence is low — both trigger fallthrough
    assert result.name is None or result.confidence < 0.9
