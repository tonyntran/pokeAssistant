"""CardScanner — two-path orchestrator: OCR-first with DINOv2 embedding fallback."""
from __future__ import annotations

import time
from pathlib import Path

from cardvision.adapter import GameAdapter
from cardvision.detector import CardDetector
from cardvision.embedder import CardEmbedder
from cardvision.index import CardIndex, BuildReport
from cardvision.exceptions import IndexNotBuiltError
from cardvision.ocr import CardOCR
from cardvision.result import ScanMatch, ScanResult

# OCR confidence gate: below this, OCR text is untrusted → falls through to embedding
OCR_CONFIDENCE_THRESHOLD = 0.9

# CLI warning threshold: print ⚠ when top embedding match is below this score
# Import this constant in cli.py rather than hardcoding 0.70 there.
EMBEDDING_WARN_THRESHOLD = 0.70


class CardScanner:
    """Identifies a card from an image using a hybrid OCR + embedding pipeline.

    Usage::

        # One-time setup (downloads ~85MB DINOv2 model + card images):
        CardScanner.build_index(adapter)

        adapter = PokemonAdapter()
        scanner = CardScanner(adapter)
        result = scanner.scan(Path("card.jpg"))

    Raises:
        IndexNotBuiltError: if build_index() has not been run for this adapter.
    """

    def __init__(self, adapter: GameAdapter) -> None:
        self._adapter = adapter
        self._detector = CardDetector()
        self._ocr = CardOCR(detector=self._detector)
        self._embedder = CardEmbedder()
        self._index = CardIndex()
        idx_path, meta_path = adapter.get_index_paths()
        self._index.load(idx_path, meta_path)

    def scan(self, image_path: Path, top_k: int = 3) -> ScanResult:
        """Identify a card from an image file.

        Tries OCR first (fast, ~50ms). Falls through to DINOv2 embedding search
        when OCR confidence is low, the result is ambiguous, or OCR finds nothing.

        Args:
            image_path: Path to a card photo (JPG/PNG).
            top_k: Maximum number of alternatives to return alongside the top match.

        Returns:
            ScanResult with top match, alternatives, and scan time in ms.

        Raises:
            ImageLoadError: if the image file cannot be opened.
            CardNotDetectedError: if no card-shaped rectangle is found in the image.
            OCRError: if EasyOCR encounters an internal failure.
            IndexNotBuiltError: if the FAISS index returns no results (empty or corrupt).
        """
        t0 = time.monotonic()
        card_image = self._detector.detect_and_warp(image_path)

        # ── OCR PATH (fast, primary) ─────────────────────────────────────────
        ocr = self._ocr.extract(card_image)
        if ocr.name and ocr.set_number and ocr.confidence >= OCR_CONFIDENCE_THRESHOLD:
            candidates = self._adapter.lookup_by_text(ocr.name, ocr.set_number)
            if len(candidates) == 1:
                return ScanResult(
                    top=ScanMatch(card=candidates[0], confidence=ocr.confidence, method="ocr"),
                    alternatives=[],
                    scan_ms=(time.monotonic() - t0) * 1000,
                )
        # 0 results, 2+ results (ambiguous), or low OCR confidence → fall through

        # ── EMBEDDING PATH (fallback) ────────────────────────────────────────
        embedding = self._embedder.embed(card_image)
        matches = self._index.query(embedding, top_k=top_k)

        if not matches:
            raise IndexNotBuiltError("Index returned no results — it may be empty or corrupt.")

        return ScanResult(
            top=ScanMatch(card=matches[0][0], confidence=matches[0][1], method="embedding"),
            alternatives=[
                ScanMatch(card=c, confidence=s, method="embedding")
                for c, s in matches[1:]
            ],
            scan_ms=(time.monotonic() - t0) * 1000,
        )

    @staticmethod
    def build_index(adapter: GameAdapter) -> BuildReport:
        """One-time setup: embed all cards in the adapter's catalog and save to disk.

        Downloads DINOv2 model weights (~85MB, cached after first run) then
        fetches and embeds all card images. Progress displayed via tqdm.
        """
        embedder = CardEmbedder()
        index = CardIndex()
        catalog = adapter.get_card_catalog()
        idx_path, meta_path = adapter.get_index_paths()
        return index.build(catalog, embedder, idx_path, meta_path)
