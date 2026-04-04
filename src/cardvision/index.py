"""CardIndex — FAISS-backed vector index for card similarity search."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import faiss
import numpy as np

from cardvision.exceptions import EmptyCatalogError, IndexNotBuiltError
from cardvision.result import CardRecord

_log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from cardvision.embedder import CardEmbedder


@dataclass
class BuildReport:
    total: int
    embedded: int
    skipped: int
    duration_seconds: float


class CardIndex:
    """Wraps a FAISS IndexFlatIP for cosine similarity search over card embeddings."""

    def __init__(self) -> None:
        self._index: faiss.IndexFlatIP | None = None
        self._catalog: list[CardRecord] = []

    @property
    def is_loaded(self) -> bool:
        return self._index is not None

    def build(
        self,
        catalog: list[CardRecord],
        embedder: "CardEmbedder",
        index_path: Path,
        meta_path: Path,
        request_delay: float = 0.1,
        max_retries: int = 3,
    ) -> BuildReport:
        """Download card images, embed each, build FAISS index, save to disk.

        Images are downloaded to memory only — never written to disk.
        A single card failure logs a warning and continues; the build never aborts.
        """
        import requests
        import time as _time
        from PIL import Image
        import io
        from tqdm import tqdm

        if not catalog:
            raise EmptyCatalogError(
                "Card catalog is empty. Import cards first: pokeassistant track --tcgcsv"
            )

        t0 = _time.monotonic()
        embeddings: list[np.ndarray] = []
        successful_cards: list[CardRecord] = []
        skipped = 0

        for card in tqdm(catalog, desc="Embedding cards", unit="card"):
            vec = None
            for attempt in range(max_retries):
                try:
                    resp = requests.get(card.image_url, timeout=10)
                    resp.raise_for_status()
                    img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                    vec = embedder.embed(img)
                    break
                except Exception as exc:
                    wait = 2 ** attempt
                    if attempt < max_retries - 1:
                        _time.sleep(wait)
                    else:
                        _log.warning("Skipping %r after %d attempts: %s", card.name, max_retries, exc)
                        skipped += 1
            if vec is not None:
                embeddings.append(vec)
                successful_cards.append(card)
            _time.sleep(request_delay)

        if not embeddings:
            raise EmptyCatalogError("All card image downloads failed. Index cannot be built.")
        mat = np.vstack(embeddings).astype("float32")
        self.build_from_embeddings(successful_cards, mat, index_path, meta_path)

        return BuildReport(
            total=len(catalog),
            embedded=len(successful_cards),
            skipped=skipped,
            duration_seconds=_time.monotonic() - t0,
        )

    def build_from_embeddings(
        self,
        catalog: list[CardRecord],
        embeddings: np.ndarray,
        index_path: Path,
        meta_path: Path,
    ) -> None:
        """Build and save a FAISS index from pre-computed embeddings.

        Used directly in tests (bypasses image downloads) and internally by build().
        embeddings must be shape (N, D) and L2-normalized.
        """
        if not catalog:
            raise EmptyCatalogError("Cannot build index from empty catalog.")

        if len(catalog) != embeddings.shape[0]:
            raise ValueError(
                f"Catalog length ({len(catalog)}) must match embeddings row count ({embeddings.shape[0]})."
            )

        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)   # cosine similarity via inner product on normalized vecs
        index.add(embeddings)

        index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, str(index_path))

        meta = [
            {
                "card_id": c.card_id,
                "name": c.name,
                "set_name": c.set_name,
                "image_url": c.image_url,
                "metadata": c.metadata,
            }
            for c in catalog
        ]
        meta_path.write_text(json.dumps(meta, indent=2))

        self._index = index
        self._catalog = catalog

    def load(self, index_path: Path, meta_path: Path) -> None:
        """Load a previously built index from disk."""
        if not index_path.exists() or not meta_path.exists():
            raise IndexNotBuiltError(
                f"Card index not found at {index_path}. "
                "Run: pokeassistant scan --build-index"
            )
        self._index = faiss.read_index(str(index_path))
        raw = json.loads(meta_path.read_text())
        self._catalog = [
            CardRecord(
                card_id=r["card_id"],
                name=r["name"],
                set_name=r["set_name"],
                image_url=r["image_url"],
                metadata=r["metadata"],
            )
            for r in raw
        ]

    def query(self, embedding: np.ndarray, top_k: int) -> list[tuple[CardRecord, float]]:
        """Search for top_k nearest cards by cosine similarity.

        Args:
            embedding: L2-normalized query vector, shape (D,).
            top_k: number of results to return.

        Returns:
            List of (CardRecord, similarity_score) sorted by descending score.
        """
        if self._index is None:
            raise IndexNotBuiltError("Index not loaded. Call load() first.")

        query = embedding.reshape(1, -1).astype("float32")
        scores, indices = self._index.search(query, top_k)

        return [
            (self._catalog[int(idx)], float(score))
            for score, idx in zip(scores[0], indices[0])
            if idx >= 0
        ]
