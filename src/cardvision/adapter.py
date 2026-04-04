"""GameAdapter — Protocol that all game-specific adapters must implement."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from cardvision.result import CardRecord


@runtime_checkable
class GameAdapter(Protocol):
    """Interface between the cardvision engine and a specific card game's data."""

    game_id: str  # e.g. "pokemon", "riftbound"

    def get_card_catalog(self) -> list[CardRecord]:
        """Return all cards with image_url set — used when building the FAISS index."""
        ...

    def get_index_paths(self) -> tuple[Path, Path]:
        """Return (faiss_index_path, metadata_json_path) for this game."""
        ...

    def lookup_by_text(self, name: str, set_number: str) -> list[CardRecord]:
        """Look up cards by OCR-extracted name and set number.

        Returns a list — multiple results indicate ambiguous matches
        (e.g. Shadowless vs Unlimited Base Set). An empty list means no match.
        """
        ...
