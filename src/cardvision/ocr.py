"""CardOCR — EasyOCR-based text extraction from card images."""
from __future__ import annotations

import re
from functools import cached_property

import numpy as np
from PIL import Image

from cardvision.detector import CardDetector
from cardvision.result import OCRExtract

# Pattern to match set numbers like "4/102", "025/198", "SV001/SV122"
_SET_NUMBER_RE = re.compile(r"\d+\s*/\s*\d+|[A-Z]{2,}\d+\s*/\s*[A-Z]{2,}\d+")


class CardOCR:
    """Extracts card name and set number from a warped card image using EasyOCR.

    extract() receives the full warped card and handles region cropping internally
    by calling CardDetector.crop_name_region() and crop_number_region(). No crop
    logic is re-implemented here.
    """

    def __init__(self, languages: list[str] | None = None) -> None:
        self._languages = languages or ["en"]
        self._detector = CardDetector()

    @cached_property
    def _reader(self):
        """Lazy-load EasyOCR reader (downloads ~150MB on first call)."""
        import easyocr
        return easyocr.Reader(self._languages, gpu=False)

    def extract(self, card: Image.Image) -> OCRExtract:
        """Extract card name and set number from a warped card image.

        Args:
            card: Full perspective-corrected card image (PIL.Image.Image).

        Returns:
            OCRExtract with name, set_number, and combined confidence.
            Fields are None when OCR finds no confident text in that region.
        """
        name_img = self._detector.crop_name_region(card)
        number_img = self._detector.crop_number_region(card)

        name, name_conf = self._read_name(name_img)
        set_number, num_conf = self._read_set_number(number_img)

        # Combined confidence: average of available readings
        confidences = [c for c in [name_conf, num_conf] if c is not None]
        combined = sum(confidences) / len(confidences) if confidences else 0.0

        return OCRExtract(name=name, set_number=set_number, confidence=combined)

    def _read_name(self, region: Image.Image) -> tuple[str | None, float | None]:
        arr = np.array(region.convert("RGB"))
        results = self._reader.readtext(arr, detail=1)
        if not results:
            return None, None
        # Pick the highest-confidence text in the name region
        best = max(results, key=lambda r: r[2])
        text = best[1].strip()
        conf = float(best[2])
        if not text or conf < 0.3:
            return None, None
        return text, conf

    def _read_set_number(self, region: Image.Image) -> tuple[str | None, float | None]:
        arr = np.array(region.convert("RGB"))
        results = self._reader.readtext(arr, detail=1)
        for _bbox, text, conf in results:
            clean = text.strip().replace(" ", "")
            if _SET_NUMBER_RE.fullmatch(clean):
                return clean, float(conf)
        return None, None
