"""Shared data types used across the cardvision package."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class CardRecord:
    """A card entry from the game adapter — game-agnostic."""
    card_id: str          # str(product_id) for Pokemon
    name: str
    set_name: str
    image_url: str
    metadata: dict[str, Any] = field(default_factory=dict)  # card_number, rarity, etc.


@dataclass
class ScanMatch:
    """A single candidate match returned by the scanner."""
    card: CardRecord
    confidence: float                          # 0.0–1.0
    method: Literal["ocr", "embedding"]        # which path produced this match


@dataclass
class ScanResult:
    """The full output of CardScanner.scan()."""
    top: ScanMatch
    alternatives: list[ScanMatch] = field(default_factory=list)
    scan_ms: float = 0.0


@dataclass
class OCRExtract:
    """Raw text extracted from a card image by CardOCR."""
    name: str | None = None
    set_number: str | None = None    # e.g. "4/102"
    confidence: float = 0.0          # 0.0–1.0; EasyOCR average word confidence
