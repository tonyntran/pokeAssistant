"""Tests for CardDetector — runs in CI (no model downloads required)."""
import pytest
from pathlib import Path
from PIL import Image, ImageDraw
from cardvision.detector import CardDetector
from cardvision.exceptions import CardNotDetectedError, ImageLoadError


def make_card_image(tmp_path: Path, angled: bool = False) -> Path:
    """Create a synthetic card-shaped image for testing."""
    img = Image.new("RGB", (800, 700), color=(80, 80, 80))
    draw = ImageDraw.Draw(img)
    # Draw a white card-shaped rectangle with a clear border
    draw.rectangle([150, 100, 550, 660], fill=(255, 255, 255), outline=(0, 0, 0), width=3)
    if angled:
        img = img.rotate(20, expand=False, fillcolor=(80, 80, 80))
    path = tmp_path / ("angled_card.png" if angled else "clean_card.png")
    img.save(path)
    return path


def test_detect_and_warp_returns_pil_image(tmp_path):
    detector = CardDetector()
    card_path = make_card_image(tmp_path)
    result = detector.detect_and_warp(card_path)
    assert isinstance(result, Image.Image)


def test_warped_card_has_portrait_orientation(tmp_path):
    detector = CardDetector()
    card_path = make_card_image(tmp_path)
    result = detector.detect_and_warp(card_path)
    w, h = result.size
    assert h > w, f"Expected portrait orientation, got {w}x{h}"


def test_crop_name_region_returns_top_strip(tmp_path):
    detector = CardDetector()
    card_path = make_card_image(tmp_path)
    card = detector.detect_and_warp(card_path)
    name_region = detector.crop_name_region(card)
    card_w, card_h = card.size
    region_w, region_h = name_region.size
    # Name region should be top ~15% of card height
    assert region_h < card_h * 0.25
    assert region_w == card_w


def test_crop_number_region_returns_bottom_strip(tmp_path):
    detector = CardDetector()
    card_path = make_card_image(tmp_path)
    card = detector.detect_and_warp(card_path)
    number_region = detector.crop_number_region(card)
    card_w, card_h = card.size
    region_w, region_h = number_region.size
    # Number region should be full-width bottom strip (~15% of height)
    assert region_w == card_w
    assert region_h < card_h * 0.25


def test_raises_image_load_error_on_bad_file(tmp_path):
    detector = CardDetector()
    bad_path = tmp_path / "not_an_image.txt"
    bad_path.write_text("this is not an image")
    with pytest.raises(ImageLoadError):
        detector.detect_and_warp(bad_path)


def test_raises_card_not_detected_on_blank_image(tmp_path):
    """A featureless image with no rectangle raises CardNotDetectedError."""
    detector = CardDetector()
    blank = Image.new("RGB", (200, 200), color=(128, 128, 128))
    path = tmp_path / "blank.png"
    blank.save(path)
    with pytest.raises(CardNotDetectedError):
        detector.detect_and_warp(path)


def test_detect_and_warp_handles_slightly_angled_card(tmp_path):
    """Detector should handle cards rotated ~20 degrees."""
    detector = CardDetector()
    card_path = make_card_image(tmp_path, angled=True)
    result = detector.detect_and_warp(card_path)
    assert isinstance(result, Image.Image)


def test_warped_card_is_exactly_400x560(tmp_path):
    """detect_and_warp always outputs exactly _WARP_WIDTH x _WARP_HEIGHT."""
    from cardvision.detector import _WARP_WIDTH, _WARP_HEIGHT
    detector = CardDetector()
    card_path = make_card_image(tmp_path)
    result = detector.detect_and_warp(card_path)
    assert result.size == (_WARP_WIDTH, _WARP_HEIGHT)
