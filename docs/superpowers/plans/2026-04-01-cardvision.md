# cardvision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `pokeassistant scan --image card.jpg` — a hybrid OCR-first + DINOv2 embedding fallback card identification pipeline living in a game-agnostic `src/cardvision/` package.

**Architecture:** `cardvision` is a standalone Python package with no knowledge of Pokemon — it exposes a `GameAdapter` Protocol that `pokeassistant/vision/PokemonAdapter` implements. The scanner tries OCR (EasyOCR) first; if confidence is low or the result is ambiguous, it falls back to DINOv2 embeddings + FAISS cosine search.

**Tech Stack:** Python 3.10+, PyTorch + DINOv2 (embedding), EasyOCR (OCR), OpenCV (card detection), FAISS-cpu (vector search), Pillow (image I/O), tqdm (progress), pytest + unittest.mock (testing)

**Spec:** `docs/superpowers/specs/2026-04-01-cardvision-design.md`

---

## File Map

**New files:**
- `src/cardvision/__init__.py` — package marker
- `src/cardvision/exceptions.py` — all custom exceptions
- `src/cardvision/result.py` — `CardRecord`, `ScanMatch`, `ScanResult`, `OCRExtract` dataclasses
- `src/cardvision/adapter.py` — `GameAdapter` Protocol
- `src/cardvision/detector.py` — `CardDetector` (OpenCV warp)
- `src/cardvision/embedder.py` — `CardEmbedder` (DINOv2)
- `src/cardvision/index.py` — `CardIndex` (FAISS build + query)
- `src/cardvision/ocr.py` — `CardOCR` (EasyOCR)
- `src/cardvision/scanner.py` — `CardScanner` (orchestrator)
- `src/pokeassistant/vision/__init__.py` — package marker
- `src/pokeassistant/vision/pokemon_adapter.py` — `PokemonAdapter`
- `tests/test_cardvision/__init__.py` — package marker
- `tests/test_cardvision/conftest.py` — pytest marks + shared fixtures
- `tests/test_cardvision/test_detector.py`
- `tests/test_cardvision/test_embedder.py` — `@pytest.mark.integration`
- `tests/test_cardvision/test_index.py`
- `tests/test_cardvision/test_ocr.py` — `@pytest.mark.integration`
- `tests/test_cardvision/test_scanner.py`
- `CHANGELOG.md`

**Modified files:**
- `pyproject.toml` — version `0.1.0` → `0.2.0`, add `[vision]` extras + tqdm
- `src/pokeassistant/config.py` — add `get_data_dir()`
- `src/pokeassistant/repositories/sqlalchemy_repo.py` — add `find_by_name_and_number()`
- `src/pokeassistant/cli.py` — refactor to subparsers, add `scan` subcommand

---

## Task 1: Project Setup — pyproject.toml, CHANGELOG, exceptions, result types

**Files:**
- Modify: `pyproject.toml`
- Create: `CHANGELOG.md`
- Create: `src/cardvision/__init__.py`
- Create: `src/cardvision/exceptions.py`
- Create: `src/cardvision/result.py`

- [ ] **Step 1: Bump version and add vision extras in pyproject.toml**

Replace the version line and add optional dependencies:

```toml
# pyproject.toml — change version
version = "0.2.0"

# add to [project.optional-dependencies]
[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-asyncio>=0.23",
    "ruff>=0.1",
    "httpx>=0.27",
]
vision = [
    "torch>=2.0",
    "torchvision>=0.15",
    "faiss-cpu>=1.7",
    "opencv-python-headless>=4.8",
    "easyocr>=1.7",
    "Pillow>=10.0",
    "tqdm>=4.65",
]
```

- [ ] **Step 2: Create CHANGELOG.md**

```markdown
# Changelog

## [0.2.0] - 2026-04-01

### Breaking Changes
- CLI refactored to subparsers. Replace:
  - `pokeassistant --product-id X --tcgcsv` → `pokeassistant track --product-id X --tcgcsv`
  - All existing flags work identically under the `track` subcommand.

### Added
- `pokeassistant scan --image card.jpg` — identify a card from a photo
- `pokeassistant scan --build-index` — build local FAISS card index from DB
- `src/cardvision/` — game-agnostic CV engine (OCR + DINOv2 embeddings)
- `[vision]` optional dependency group
```

- [ ] **Step 3: Create src/cardvision/__init__.py**

```python
"""cardvision — game-agnostic card scanning engine."""
```

- [ ] **Step 4: Create src/cardvision/exceptions.py**

```python
"""All custom exceptions for the cardvision package."""


class CardVisionError(Exception):
    """Base class for all cardvision errors."""


class IndexNotBuiltError(CardVisionError):
    """Raised when the FAISS index file does not exist on disk."""


class CardNotDetectedError(CardVisionError):
    """Raised when OpenCV cannot find a card-shaped rectangle in the image."""


class EmptyCatalogError(CardVisionError):
    """Raised by CardIndex.build() when the adapter returns an empty catalog."""


class ImageLoadError(CardVisionError):
    """Raised when Pillow cannot open or read the provided image file."""
```

- [ ] **Step 5: Create src/cardvision/result.py**

```python
"""Shared data types used across the cardvision package."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class CardRecord:
    """A card entry from the game adapter — game-agnostic."""
    card_id: str          # str(product_id) for Pokemon
    name: str
    set_name: str
    image_url: str
    metadata: dict = field(default_factory=dict)  # card_number, rarity, etc.


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
    name: str | None
    set_number: str | None    # e.g. "4/102"
    confidence: float         # 0.0–1.0; EasyOCR average word confidence
```

- [ ] **Step 6: Verify the new files are importable**

```bash
cd /home/ttran/projects/pokeAssistant
python -c "from cardvision.exceptions import IndexNotBuiltError; from cardvision.result import ScanResult; print('ok')"
```
Expected: `ok`

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml CHANGELOG.md src/cardvision/
git commit -m "feat(cardvision): project setup — exceptions, result types, v0.2.0"
```

---

## Task 2: Config and Repository Additions

**Files:**
- Modify: `src/pokeassistant/config.py`
- Modify: `src/pokeassistant/repositories/sqlalchemy_repo.py`
- Test: `tests/test_repository.py` (extend existing)

- [ ] **Step 1: Write the failing test for find_by_name_and_number**

Add to `tests/test_repository.py` (look at the existing test file structure and add alongside existing tests):

```python
def test_find_by_name_and_number_returns_exact_match(session, sample_product):
    """find_by_name_and_number returns products matching both name and card_number."""
    repo = SQLAlchemyRepository(session)
    results = repo.find_by_name_and_number("Charizard", "4/102")
    assert len(results) == 1
    assert results[0].name == "Charizard"
    assert results[0].card_number == "4/102"


def test_find_by_name_and_number_returns_empty_when_no_match(session):
    """find_by_name_and_number returns empty list when no card matches."""
    repo = SQLAlchemyRepository(session)
    results = repo.find_by_name_and_number("Nonexistent", "999/999")
    assert results == []


def test_find_by_name_and_number_returns_multiple_when_ambiguous(session):
    """find_by_name_and_number returns all matches for same name+number (e.g. Shadowless)."""
    repo = SQLAlchemyRepository(session)
    # Add a second Charizard with same card_number but different product_id
    from pokeassistant.models import Product
    session.add(Product(
        product_id=99999,
        name="Charizard",
        card_number="4/102",
        group_name="Base Set Shadowless",
    ))
    session.commit()
    results = repo.find_by_name_and_number("Charizard", "4/102")
    assert len(results) == 2
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
pytest tests/test_repository.py::test_find_by_name_and_number_returns_exact_match -v
```
Expected: `FAILED` — `AttributeError: 'SQLAlchemyRepository' object has no attribute 'find_by_name_and_number'`

- [ ] **Step 3: Add find_by_name_and_number to sqlalchemy_repo.py**

Open `src/pokeassistant/repositories/sqlalchemy_repo.py` and add this method alongside the existing `search()` method:

```python
def find_by_name_and_number(self, name: str, card_number: str) -> list[Product]:
    """Find products matching both name (case-insensitive) and card_number exactly.

    Used by PokemonAdapter.lookup_by_text() for OCR-based card identification.
    Does NOT use search() — that method has a hardcoded .limit(20) which would
    silently drop results for common names like 'Pikachu' across many sets.
    """
    return (
        self.session.query(Product)
        .filter(
            Product.name.ilike(f"%{name}%"),
            Product.card_number == card_number,
        )
        .all()
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_repository.py::test_find_by_name_and_number_returns_exact_match tests/test_repository.py::test_find_by_name_and_number_returns_empty_when_no_match tests/test_repository.py::test_find_by_name_and_number_returns_multiple_when_ambiguous -v
```
Expected: all 3 `PASSED`

- [ ] **Step 5: Add get_data_dir() to config.py**

Open `src/pokeassistant/config.py` and add after the existing `DEFAULT_DB_PATH` line:

```python
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"


def get_data_dir() -> Path:
    """Returns the directory used for generated data files (FAISS index, etc.).

    Override with POKEASSISTANT_DATA_DIR environment variable for deployed installs.
    """
    return Path(os.environ.get("POKEASSISTANT_DATA_DIR", str(DEFAULT_DATA_DIR)))
```

- [ ] **Step 6: Verify config change is importable**

```bash
python -c "from pokeassistant.config import get_data_dir; print(get_data_dir())"
```
Expected: prints the `data/` path under the project root

- [ ] **Step 7: Commit**

```bash
git add src/pokeassistant/config.py src/pokeassistant/repositories/sqlalchemy_repo.py tests/test_repository.py
git commit -m "feat: add get_data_dir() and find_by_name_and_number() for cardvision"
```

---

## Task 3: CardDetector — OpenCV Card Detection + Perspective Warp

**Files:**
- Create: `src/cardvision/detector.py`
- Create: `tests/test_cardvision/__init__.py`
- Create: `tests/test_cardvision/conftest.py`
- Create: `tests/test_cardvision/test_detector.py`

- [ ] **Step 1: Create test infrastructure**

Create `tests/test_cardvision/__init__.py` (empty):
```python
```

Create `tests/test_cardvision/conftest.py`:
```python
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: mark test as requiring model downloads (skip in CI with -m 'not integration')"
    )
```

- [ ] **Step 2: Write the failing tests for CardDetector**

Create `tests/test_cardvision/test_detector.py`:
```python
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
    path = tmp_path / ("angled_card.jpg" if angled else "clean_card.jpg")
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


def test_crop_number_region_returns_bottom_right(tmp_path):
    detector = CardDetector()
    card_path = make_card_image(tmp_path)
    card = detector.detect_and_warp(card_path)
    number_region = detector.crop_number_region(card)
    card_w, card_h = card.size
    region_w, region_h = number_region.size
    # Number region should be bottom-right quarter
    assert region_w < card_w * 0.6
    assert region_h < card_h * 0.25


def test_raises_image_load_error_on_bad_file(tmp_path):
    detector = CardDetector()
    bad_path = tmp_path / "not_an_image.txt"
    bad_path.write_text("this is not an image")
    with pytest.raises(ImageLoadError):
        detector.detect_and_warp(bad_path)
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
pytest tests/test_cardvision/test_detector.py -v
```
Expected: `ERROR` — `ModuleNotFoundError: No module named 'cardvision.detector'`

- [ ] **Step 4: Create src/cardvision/detector.py**

```python
"""CardDetector — finds a card in an image and applies perspective correction."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

from cardvision.exceptions import CardNotDetectedError, ImageLoadError

# Target output size after warp (standard card proportions 63mm × 88mm)
_WARP_WIDTH = 400
_WARP_HEIGHT = 560

# Fraction of card height used for each crop region
_NAME_REGION_TOP = 0.0
_NAME_REGION_BOTTOM = 0.15
_NUMBER_REGION_TOP = 0.85
_NUMBER_REGION_BOTTOM = 1.0
_NUMBER_REGION_LEFT = 0.5


class CardDetector:
    """Locates a card in a photo, warps it flat, and exposes crop helpers."""

    def detect_and_warp(self, image_path: Path) -> Image.Image:
        """Find the largest card-shaped rectangle and apply perspective correction.

        Args:
            image_path: Path to input image (JPG, PNG, etc.)

        Returns:
            PIL.Image.Image — perspective-corrected card at fixed size.

        Raises:
            ImageLoadError: if the file cannot be opened.
            CardNotDetectedError: if no card-shaped rectangle is found.
        """
        try:
            pil_img = Image.open(image_path).convert("RGB")
        except (UnidentifiedImageError, OSError) as exc:
            raise ImageLoadError(f"Could not read image: {image_path}") from exc

        img = np.array(pil_img)
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        card_corners = None
        for cnt in contours[:10]:
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
            if len(approx) == 4 and cv2.contourArea(cnt) > 5000:
                card_corners = approx.reshape(4, 2).astype("float32")
                break

        if card_corners is None:
            raise CardNotDetectedError(
                "No card found. Ensure the card fills most of the frame."
            )

        dst = np.array(
            [[0, 0], [_WARP_WIDTH, 0], [_WARP_WIDTH, _WARP_HEIGHT], [0, _WARP_HEIGHT]],
            dtype="float32",
        )
        card_corners = _order_corners(card_corners)
        M = cv2.getPerspectiveTransform(card_corners, dst)
        warped = cv2.warpPerspective(img, M, (_WARP_WIDTH, _WARP_HEIGHT))
        return Image.fromarray(warped)

    def crop_name_region(self, card: Image.Image) -> Image.Image:
        """Return the top strip of the card where the card name lives (~15%)."""
        w, h = card.size
        return card.crop((0, int(h * _NAME_REGION_TOP), w, int(h * _NAME_REGION_BOTTOM)))

    def crop_number_region(self, card: Image.Image) -> Image.Image:
        """Return the bottom-right corner where the set number lives."""
        w, h = card.size
        return card.crop((
            int(w * _NUMBER_REGION_LEFT),
            int(h * _NUMBER_REGION_TOP),
            w,
            int(h * _NUMBER_REGION_BOTTOM),
        ))


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """Order corners as: top-left, top-right, bottom-right, bottom-left."""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_cardvision/test_detector.py -v
```
Expected: all `PASSED`

- [ ] **Step 6: Commit**

```bash
git add src/cardvision/detector.py tests/test_cardvision/
git commit -m "feat(cardvision): CardDetector — OpenCV perspective warp"
```

---

## Task 4: CardEmbedder — DINOv2 Embedding

**Files:**
- Create: `src/cardvision/embedder.py`
- Create: `tests/test_cardvision/test_embedder.py`

- [ ] **Step 1: Write the failing integration tests**

Create `tests/test_cardvision/test_embedder.py`:
```python
"""Integration tests for CardEmbedder — requires DINOv2 model download (~85MB).

Run with: pytest tests/test_cardvision/test_embedder.py -m integration -v
Skip in CI with: pytest -m 'not integration'
"""
import numpy as np
import pytest
from pathlib import Path
from PIL import Image

from cardvision.embedder import CardEmbedder


@pytest.mark.integration
def test_embed_returns_correct_shape(tmp_path):
    img_path = tmp_path / "card.jpg"
    Image.new("RGB", (400, 560), color=(200, 200, 200)).save(img_path)
    embedder = CardEmbedder()
    vec = embedder.embed(img_path)
    assert vec.shape == (384,), f"Expected shape (384,), got {vec.shape}"


@pytest.mark.integration
def test_embed_returns_float32(tmp_path):
    img_path = tmp_path / "card.jpg"
    Image.new("RGB", (400, 560)).save(img_path)
    embedder = CardEmbedder()
    vec = embedder.embed(img_path)
    assert vec.dtype == np.float32


@pytest.mark.integration
def test_embed_is_l2_normalized(tmp_path):
    img_path = tmp_path / "card.jpg"
    Image.new("RGB", (400, 560)).save(img_path)
    embedder = CardEmbedder()
    vec = embedder.embed(img_path)
    norm = np.linalg.norm(vec)
    assert abs(norm - 1.0) < 1e-5, f"Expected L2 norm ≈ 1.0, got {norm}"


@pytest.mark.integration
def test_same_image_produces_identical_embeddings(tmp_path):
    img_path = tmp_path / "card.jpg"
    Image.new("RGB", (400, 560), color=(100, 150, 200)).save(img_path)
    embedder = CardEmbedder()
    v1 = embedder.embed(img_path)
    v2 = embedder.embed(img_path)
    cosine_sim = float(np.dot(v1, v2))
    assert cosine_sim > 0.999, f"Same image should produce identical vectors, got {cosine_sim}"


@pytest.mark.integration
def test_embed_batch_returns_correct_shape(tmp_path):
    paths = []
    for i in range(3):
        p = tmp_path / f"card_{i}.jpg"
        Image.new("RGB", (400, 560), color=(i * 50, 100, 100)).save(p)
        paths.append(p)
    embedder = CardEmbedder()
    batch = embedder.embed_batch(paths)
    assert batch.shape == (3, 384)
    # Each row should be L2-normalized
    norms = np.linalg.norm(batch, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5)
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_cardvision/test_embedder.py -m integration -v
```
Expected: `ERROR — ModuleNotFoundError: No module named 'cardvision.embedder'`

- [ ] **Step 3: Create src/cardvision/embedder.py**

```python
"""CardEmbedder — wraps DINOv2 ViT-S/14 to produce L2-normalized image embeddings."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torchvision import transforms


_TRANSFORM = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

_EMBEDDING_DIM = 384  # DINOv2 ViT-S/14 output dimension


class CardEmbedder:
    """Converts card images to L2-normalized embedding vectors using DINOv2."""

    def __init__(self, model: str = "dinov2_vits14") -> None:
        self._model_name = model
        self._model: torch.nn.Module | None = None  # lazy load

    def _get_model(self) -> torch.nn.Module:
        if self._model is None:
            self._model = torch.hub.load("facebookresearch/dinov2", self._model_name)
            self._model.eval()
        return self._model

    def embed(self, image: Path | Image.Image) -> np.ndarray:
        """Embed a single image.

        Args:
            image: Path to image file or a PIL.Image.Image.

        Returns:
            np.ndarray of shape (384,), dtype float32, L2-normalized.
        """
        if isinstance(image, Path):
            image = Image.open(image).convert("RGB")
        tensor = _TRANSFORM(image).unsqueeze(0)
        with torch.no_grad():
            vec = self._get_model()(tensor).squeeze(0).numpy().astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def embed_batch(self, images: list[Path], batch_size: int = 32) -> np.ndarray:
        """Embed a list of images, returning shape (N, 384), L2-normalized.

        Args:
            images: list of Paths to image files.
            batch_size: images processed per forward pass.

        Returns:
            np.ndarray of shape (N, 384), dtype float32, each row L2-normalized.
        """
        all_vecs: list[np.ndarray] = []
        for i in range(0, len(images), batch_size):
            batch_paths = images[i : i + batch_size]
            tensors = torch.stack([
                _TRANSFORM(Image.open(p).convert("RGB")) for p in batch_paths
            ])
            with torch.no_grad():
                vecs = self._get_model()(tensors).numpy().astype(np.float32)
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1.0, norms)
            all_vecs.append(vecs / norms)
        return np.vstack(all_vecs)
```

- [ ] **Step 4: Run integration tests (requires internet + ~85MB download on first run)**

```bash
pytest tests/test_cardvision/test_embedder.py -m integration -v
```
Expected: all `PASSED` (first run will download DINOv2 weights)

- [ ] **Step 5: Commit**

```bash
git add src/cardvision/embedder.py tests/test_cardvision/test_embedder.py
git commit -m "feat(cardvision): CardEmbedder — DINOv2 ViT-S/14 image embeddings"
```

---

## Task 5: CardIndex — FAISS Build + Query

**Files:**
- Create: `src/cardvision/index.py`
- Create: `tests/test_cardvision/test_index.py`

- [ ] **Step 1: Write the failing tests (runs in CI — no model needed)**

Create `tests/test_cardvision/test_index.py`:
```python
"""Unit tests for CardIndex — runs in CI using synthetic embeddings (no model downloads)."""
import json
import numpy as np
import pytest
from pathlib import Path

from cardvision.index import CardIndex
from cardvision.result import CardRecord
from cardvision.exceptions import IndexNotBuiltError


FAKE_CARDS = [
    CardRecord(card_id="1", name="Charizard", set_name="Base Set", image_url="", metadata={"card_number": "4/102"}),
    CardRecord(card_id="2", name="Pikachu", set_name="Base Set", image_url="", metadata={"card_number": "58/102"}),
    CardRecord(card_id="3", name="Blastoise", set_name="Base Set", image_url="", metadata={"card_number": "2/102"}),
]


def make_fake_embeddings(n: int = 3, dim: int = 384) -> np.ndarray:
    rng = np.random.default_rng(42)
    vecs = rng.random((n, dim)).astype("float32")
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / norms


def test_build_and_query_returns_exact_match(tmp_path):
    embeddings = make_fake_embeddings(3)
    index = CardIndex()
    idx_path = tmp_path / "test.index"
    meta_path = tmp_path / "test.json"

    index.build_from_embeddings(FAKE_CARDS, embeddings, idx_path, meta_path)
    index.load(idx_path, meta_path)

    results = index.query(embeddings[0], top_k=3)
    assert results[0][0].card_id == "1", "Top match should be the card whose embedding was queried"
    assert results[0][1] > 0.999, f"Expected near-perfect similarity, got {results[0][1]}"


def test_query_returns_top_k_results(tmp_path):
    embeddings = make_fake_embeddings(3)
    index = CardIndex()
    idx_path = tmp_path / "test.index"
    meta_path = tmp_path / "test.json"

    index.build_from_embeddings(FAKE_CARDS, embeddings, idx_path, meta_path)
    index.load(idx_path, meta_path)

    results = index.query(embeddings[0], top_k=2)
    assert len(results) == 2


def test_results_ordered_by_descending_confidence(tmp_path):
    embeddings = make_fake_embeddings(3)
    index = CardIndex()
    idx_path = tmp_path / "test.index"
    meta_path = tmp_path / "test.json"

    index.build_from_embeddings(FAKE_CARDS, embeddings, idx_path, meta_path)
    index.load(idx_path, meta_path)

    results = index.query(embeddings[0], top_k=3)
    scores = [r[1] for r in results]
    assert scores == sorted(scores, reverse=True), "Results must be sorted by descending confidence"


def test_load_raises_index_not_built_error(tmp_path):
    index = CardIndex()
    with pytest.raises(IndexNotBuiltError):
        index.load(tmp_path / "missing.index", tmp_path / "missing.json")


def test_metadata_persisted_correctly(tmp_path):
    embeddings = make_fake_embeddings(3)
    index = CardIndex()
    idx_path = tmp_path / "test.index"
    meta_path = tmp_path / "test.json"

    index.build_from_embeddings(FAKE_CARDS, embeddings, idx_path, meta_path)
    index.load(idx_path, meta_path)

    results = index.query(embeddings[1], top_k=1)
    assert results[0][0].name == "Pikachu"
    assert results[0][0].metadata["card_number"] == "58/102"
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_cardvision/test_index.py -v
```
Expected: `ERROR — ModuleNotFoundError: No module named 'cardvision.index'`

- [ ] **Step 3: Create src/cardvision/index.py**

```python
"""CardIndex — FAISS-backed vector index for card similarity search."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import faiss
import numpy as np
from tqdm import tqdm

from cardvision.exceptions import EmptyCatalogError, IndexNotBuiltError
from cardvision.result import CardRecord

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
                        print(f"\n  ⚠ Skipping {card.name!r}: {exc}")
                        skipped += 1
            if vec is not None:
                embeddings.append(vec)
                successful_cards.append(card)
            _time.sleep(request_delay)

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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_cardvision/test_index.py -v
```
Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/cardvision/index.py tests/test_cardvision/test_index.py
git commit -m "feat(cardvision): CardIndex — FAISS IndexFlatIP build + query"
```

---

## Task 6: CardOCR — EasyOCR Text Extraction

**Files:**
- Create: `src/cardvision/ocr.py`
- Create: `tests/test_cardvision/test_ocr.py`

- [ ] **Step 1: Write the failing integration tests**

Create `tests/test_cardvision/test_ocr.py`:
```python
"""Integration tests for CardOCR — requires EasyOCR model download (~150MB).

Run with: pytest tests/test_cardvision/test_ocr.py -m integration -v
"""
import pytest
from PIL import Image, ImageDraw, ImageFont

from cardvision.ocr import CardOCR
from cardvision.result import OCRExtract
from cardvision.detector import CardDetector


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
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_cardvision/test_ocr.py -m integration -v
```
Expected: `ERROR — ModuleNotFoundError: No module named 'cardvision.ocr'`

- [ ] **Step 3: Create src/cardvision/ocr.py**

```python
"""CardOCR — EasyOCR-based text extraction from card images."""
from __future__ import annotations

import re
from functools import cached_property

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
        results = self._reader.readtext(region, detail=1)
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
        results = self._reader.readtext(region, detail=1)
        for _bbox, text, conf in results:
            clean = text.strip().replace(" ", "")
            if _SET_NUMBER_RE.fullmatch(clean):
                return clean, float(conf)
        return None, None
```

- [ ] **Step 4: Run integration tests (requires ~150MB EasyOCR download on first run)**

```bash
pytest tests/test_cardvision/test_ocr.py -m integration -v
```
Expected: all `PASSED`

- [ ] **Step 5: Commit**

```bash
git add src/cardvision/ocr.py tests/test_cardvision/test_ocr.py
git commit -m "feat(cardvision): CardOCR — EasyOCR name + set number extraction"
```

---

## Task 7: GameAdapter Protocol + CardScanner

**Files:**
- Create: `src/cardvision/adapter.py`
- Create: `src/cardvision/scanner.py`
- Create: `tests/test_cardvision/test_scanner.py`

- [ ] **Step 1: Create src/cardvision/adapter.py**

```python
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
```

- [ ] **Step 2: Write the failing scanner tests (runs in CI — all mocked)**

Create `tests/test_cardvision/test_scanner.py`:
```python
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


def make_scanner(mock_adapter, monkeypatch):
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


def test_ocr_path_used_when_high_confidence(mock_adapter, monkeypatch, tmp_path):
    """Path 1: OCR succeeds with confidence >= threshold and single lookup match."""
    scanner = make_scanner(mock_adapter, monkeypatch)
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


def test_falls_through_to_embedding_when_ocr_low_confidence(mock_adapter, monkeypatch, tmp_path):
    """Path 2: OCR confidence < OCR_CONFIDENCE_THRESHOLD triggers embedding fallback."""
    scanner = make_scanner(mock_adapter, monkeypatch)
    scanner._ocr.extract.return_value = OCRExtract(
        name="Charizard", set_number="4/102", confidence=0.5  # below threshold
    )
    scanner._index.query.return_value = [(CHARIZARD, 0.92)]

    img = tmp_path / "card.jpg"
    Image.new("RGB", (400, 560)).save(img)
    result = scanner.scan(img)

    assert result.top.method == "embedding"
    scanner._embedder.embed.assert_called_once()


def test_falls_through_to_embedding_when_ocr_ambiguous(mock_adapter, monkeypatch, tmp_path):
    """Path 3: lookup_by_text returns 2+ results (Shadowless vs Unlimited) → embedding."""
    scanner = make_scanner(mock_adapter, monkeypatch)
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


def test_falls_through_to_embedding_when_ocr_returns_none(mock_adapter, monkeypatch, tmp_path):
    """Path 4: OCR extracts nothing (foil/blur) → silent fallback to embedding."""
    scanner = make_scanner(mock_adapter, monkeypatch)
    scanner._ocr.extract.return_value = OCRExtract(name=None, set_number=None, confidence=0.0)
    scanner._index.query.return_value = [(PIKACHU, 0.91)]

    img = tmp_path / "card.jpg"
    Image.new("RGB", (400, 560)).save(img)
    result = scanner.scan(img)

    assert result.top.method == "embedding"
    assert result.top.card.card_id == "3"


def test_low_embedding_confidence_result_still_returned(mock_adapter, monkeypatch, tmp_path):
    """Path 5: low embedding confidence → ScanResult returned; CLI checks threshold."""
    scanner = make_scanner(mock_adapter, monkeypatch)
    scanner._ocr.extract.return_value = OCRExtract(name=None, set_number=None, confidence=0.0)
    low_conf = EMBEDDING_WARN_THRESHOLD - 0.1
    scanner._index.query.return_value = [(CHARIZARD, low_conf)]

    img = tmp_path / "card.jpg"
    Image.new("RGB", (400, 560)).save(img)
    result = scanner.scan(img)

    assert isinstance(result, ScanResult)
    assert result.top.confidence < EMBEDDING_WARN_THRESHOLD


def test_scan_result_has_scan_ms(mock_adapter, monkeypatch, tmp_path):
    scanner = make_scanner(mock_adapter, monkeypatch)
    scanner._ocr.extract.return_value = OCRExtract(name=None, set_number=None, confidence=0.0)
    scanner._index.query.return_value = [(CHARIZARD, 0.90)]

    img = tmp_path / "card.jpg"
    Image.new("RGB", (400, 560)).save(img)
    result = scanner.scan(img)

    assert result.scan_ms >= 0
```

- [ ] **Step 3: Run to confirm failure**

```bash
pytest tests/test_cardvision/test_scanner.py -v
```
Expected: `ERROR — ModuleNotFoundError: No module named 'cardvision.scanner'`

- [ ] **Step 4: Create src/cardvision/scanner.py**

```python
"""CardScanner — two-path orchestrator: OCR-first with DINOv2 embedding fallback."""
from __future__ import annotations

import time
from pathlib import Path

from cardvision.adapter import GameAdapter
from cardvision.detector import CardDetector
from cardvision.embedder import CardEmbedder
from cardvision.index import CardIndex, BuildReport
from cardvision.ocr import CardOCR
from cardvision.result import ScanMatch, ScanResult

# OCR confidence gate: below this, OCR text is untrusted → falls through to embedding
OCR_CONFIDENCE_THRESHOLD = 0.9

# CLI warning threshold: print ⚠ when top embedding match is below this score
# Import this constant in cli.py rather than hardcoding 0.70 there.
EMBEDDING_WARN_THRESHOLD = 0.70


class CardScanner:
    """Identifies a card from an image using a hybrid OCR + embedding pipeline.

    Usage:
        adapter = PokemonAdapter()
        scanner = CardScanner(adapter)
        result = scanner.scan(Path("card.jpg"))
    """

    def __init__(self, adapter: GameAdapter) -> None:
        self._adapter = adapter
        self._detector = CardDetector()
        self._ocr = CardOCR()
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

        return ScanResult(
            top=ScanMatch(card=matches[0][0], confidence=matches[0][1], method="embedding"),
            alternatives=[
                ScanMatch(card=c, confidence=s, method="embedding")
                for c, s in matches[1:]
            ],
            scan_ms=(time.monotonic() - t0) * 1000,
        )

    @classmethod
    def build_index(cls, adapter: GameAdapter) -> BuildReport:
        """One-time setup: embed all cards in the adapter's catalog and save to disk.

        Downloads DINOv2 model weights (~85MB, cached after first run) then
        fetches and embeds all card images. Progress displayed via tqdm.
        """
        embedder = CardEmbedder()
        index = CardIndex()
        catalog = adapter.get_card_catalog()
        idx_path, meta_path = adapter.get_index_paths()
        return index.build(catalog, embedder, idx_path, meta_path)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_cardvision/test_scanner.py -v
```
Expected: all `PASSED`

- [ ] **Step 6: Commit**

```bash
git add src/cardvision/adapter.py src/cardvision/scanner.py tests/test_cardvision/test_scanner.py
git commit -m "feat(cardvision): CardScanner — two-path OCR + embedding orchestrator"
```

---

## Task 8: PokemonAdapter

**Files:**
- Create: `src/pokeassistant/vision/__init__.py`
- Create: `src/pokeassistant/vision/pokemon_adapter.py`

- [ ] **Step 1: Create src/pokeassistant/vision/__init__.py**

```python
"""Pokemon-specific adapter for the cardvision engine."""
from pokeassistant.vision.pokemon_adapter import PokemonAdapter

__all__ = ["PokemonAdapter"]
```

- [ ] **Step 2: Create src/pokeassistant/vision/pokemon_adapter.py**

```python
"""PokemonAdapter — bridges the pokeassistant DB to the cardvision engine."""
from __future__ import annotations

from pathlib import Path

from pokeassistant.config import get_data_dir
from pokeassistant.database import get_engine, get_session_factory
from pokeassistant.models import Product
from pokeassistant.repositories.sqlalchemy_repo import SQLAlchemyRepository
from cardvision.result import CardRecord


class PokemonAdapter:
    """Implements GameAdapter Protocol using the pokeassistant SQLite database."""

    game_id = "pokemon"

    def get_card_catalog(self) -> list[CardRecord]:
        """Return all products with image_url set, as CardRecords.

        These are used by CardIndex.build() to download images and create embeddings.
        Filters only by image_url IS NOT NULL — no product_type filter, per spec §7.
        """
        session = get_session_factory(get_engine())()
        try:
            products = (
                session.query(Product)
                .filter(Product.image_url.isnot(None))
                .all()
            )
            return [_product_to_record(p) for p in products]
        finally:
            session.close()

    def get_index_paths(self) -> tuple[Path, Path]:
        """Return paths to the Pokemon FAISS index and metadata file."""
        data_dir = get_data_dir()
        return data_dir / "pokemon.index", data_dir / "pokemon_cards.json"

    def lookup_by_text(self, name: str, set_number: str) -> list[CardRecord]:
        """Find cards matching both name and set number using a purpose-built query.

        Uses find_by_name_and_number() — NOT repo.search() which has .limit(20).
        Returns multiple cards when the same name+number maps to different printings
        (e.g. Shadowless vs Unlimited Base Set).
        """
        session = get_session_factory(get_engine())()
        try:
            repo = SQLAlchemyRepository(session)
            products = repo.find_by_name_and_number(name, set_number)
            return [_product_to_record(p) for p in products]
        finally:
            session.close()


def _product_to_record(p: Product) -> CardRecord:
    return CardRecord(
        card_id=str(p.product_id),
        name=p.name,
        set_name=p.group_name or "",
        image_url=p.image_url or "",
        metadata={
            "card_number": p.card_number,
            "rarity": p.rarity,
        },
    )
```

- [ ] **Step 3: Verify the adapter is importable**

```bash
python -c "from pokeassistant.vision import PokemonAdapter; a = PokemonAdapter(); print(a.game_id)"
```
Expected: `pokemon`

- [ ] **Step 4: Commit**

```bash
git add src/pokeassistant/vision/
git commit -m "feat(pokeassistant): PokemonAdapter — bridges DB to cardvision engine"
```

---

## Task 9: CLI Refactor — Subparsers + Scan Subcommand

**Files:**
- Modify: `src/pokeassistant/cli.py`
- Test: `tests/test_cli.py` (extend existing)

- [ ] **Step 1: Migrate existing tests to track subcommand**

Open `tests/test_cli.py`. Every existing call that uses the flat-flag format must be updated to use the `track` subcommand. Examples:

```python
# Before (will break after subparser refactor):
parse_args(["--product-id", "593355", "--tcgcsv"])
main(["--product-id", "593355", "--tcgcsv"])

# After:
parse_args(["track", "--product-id", "593355", "--tcgcsv"])
main(["track", "--product-id", "593355", "--tcgcsv"])
```

Apply this rename to ALL existing test calls before writing any new tests. Run the suite to take inventory:

```bash
pytest tests/test_cli.py -v
```
Expected: **most tests FAIL at this point** — this is correct. The existing `cli.py` still uses flat flags, so `parse_args(["track", ...])` will fail with `SystemExit`. This step is purely to update the test file and record which tests exist before you start rewriting `cli.py`. The tests will go green in Step 4b after the refactor.

Also verify that every `add_argument()` call in the existing `parse_args()` is reflected in the `_build_track_parser` template below. Add any missing flags before proceeding.

- [ ] **Step 2: Write failing CLI tests**

Check the existing `tests/test_cli.py` for its structure, then add these tests:

```python
def test_track_subcommand_requires_product_id():
    """Old flags work under `track` subcommand."""
    with pytest.raises(SystemExit):
        parse_args(["track"])  # missing --product-id


def test_scan_image_and_build_index_are_mutually_exclusive():
    """--image and --build-index cannot be used together."""
    with pytest.raises(SystemExit):
        parse_args(["scan", "--image", "card.jpg", "--build-index"])


def test_scan_requires_one_of_image_or_build_index():
    """scan subcommand requires either --image or --build-index."""
    with pytest.raises(SystemExit):
        parse_args(["scan"])


def test_scan_image_parses_path():
    args = parse_args(["scan", "--image", "card.jpg"])
    assert args.image == "card.jpg"
    assert args.command == "scan"


def test_scan_build_index_flag():
    args = parse_args(["scan", "--build-index"])
    assert args.build_index is True


def test_scan_top_default_is_3():
    args = parse_args(["scan", "--image", "card.jpg"])
    assert args.top == 3


def test_track_parses_product_id():
    args = parse_args(["track", "--product-id", "3816", "--tcgcsv"])
    assert args.product_id == 3816
    assert args.tcgcsv is True
```

- [ ] **Step 3: Run to confirm new tests fail**

```bash
pytest tests/test_cli.py -v -k "track_subcommand or mutually_exclusive or scan_image or scan_build or scan_top or track_parses"
```
Expected: multiple `FAILED` — no subparsers yet

- [ ] **Step 4 (preliminary): Read and record the existing main() body before overwriting**

```bash
cat src/pokeassistant/cli.py
```

Read the output carefully and keep it visible — you will paste the body of `main()` into `run_track()` in the next step. Once you write the new `cli.py`, the old `main()` body is gone from the working tree (still in git, but harder to reference mid-task).

- [ ] **Step 4: Refactor cli.py to use subparsers**

Replace the entire `parse_args()` function and `main()` in `src/pokeassistant/cli.py` with the following. All existing `track` logic moves into `run_track()` unchanged:

```python
"""CLI entry point for pokeAssistant."""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

from pokeassistant.config import get_db_path
from pokeassistant.database import get_engine, get_session_factory
from pokeassistant.repositories import SQLAlchemyRepository
from pokeassistant.models import Product


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pokeassistant",
        description="Pokemon TCG price tracking and analysis tool",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    _build_track_parser(subparsers)
    _build_scan_parser(subparsers)

    return parser.parse_args(argv)


def _build_track_parser(subparsers) -> None:
    p = subparsers.add_parser("track", help="Scrape and track prices for a product")
    p.add_argument("--product-id", type=int, required=True, help="TCGPlayer product ID")
    p.add_argument("--group-id", type=int, default=None)
    p.add_argument("--scrape", action="store_true")
    p.add_argument("--tcgcsv", action="store_true")
    p.add_argument("--trends", action="store_true")
    p.add_argument("--pricecharting", action="store_true")
    p.add_argument("--gemrate", action="store_true")
    p.add_argument("--all", action="store_true")
    p.add_argument("--card-name", type=str, default=None)
    p.add_argument("--no-headless", action="store_true")
    p.add_argument("--keyword", action="append", default=[])


def _build_scan_parser(subparsers) -> None:
    p = subparsers.add_parser("scan", help="Identify a card from an image")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--image", type=str, metavar="PATH", help="Path to card image")
    group.add_argument("--build-index", action="store_true", help="Build FAISS index from DB")
    p.add_argument("--top", type=int, default=3, help="Number of matches to show (default: 3)")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    if args.command == "track":
        run_track(args)
    elif args.command == "scan":
        run_scan(args)


def run_scan(args: argparse.Namespace) -> None:
    """Handle the scan subcommand."""
    try:
        from cardvision.scanner import CardScanner, EMBEDDING_WARN_THRESHOLD
        from cardvision.exceptions import IndexNotBuiltError
        from pokeassistant.vision import PokemonAdapter
    except ImportError:
        print("Vision dependencies not installed.", file=sys.stderr)
        print("Run: pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu", file=sys.stderr)
        print("Then: pip install 'pokeassistant[vision]'", file=sys.stderr)
        sys.exit(1)

    adapter = PokemonAdapter()

    if args.build_index:
        _run_build_index(CardScanner, adapter)
        return

    # First-run: check for missing index and offer to build
    idx_path, _ = adapter.get_index_paths()
    if not idx_path.exists():
        print("No card index found.")
        answer = input("Build it now? Downloads DINOv2 model (~85MB) + card images (~5 min). [y/N] ")
        if answer.strip().lower() == "y":
            _run_build_index(CardScanner, adapter)
        else:
            print("Run: pokeassistant scan --build-index")
            sys.exit(0)

    # Announce model downloads on first run
    import torch
    from pathlib import Path as _Path
    hub_dir = _Path(torch.hub.get_dir())
    if not any(hub_dir.glob("facebookresearch_dinov2*")):
        print("Loading model weights (first run only, ~85MB)...")
    if not (_Path.home() / ".EasyOCR" / "model" / "english_g2.pth").exists():
        print("Loading OCR model (first run only, ~150MB)...")

    scanner = CardScanner(adapter)
    result = scanner.scan(Path(args.image), top_k=args.top)

    # Look up market price from DB using card_id (product_id for Pokemon)
    market_cents = _get_market_price(int(result.top.card.card_id))
    _print_result(result, EMBEDDING_WARN_THRESHOLD, market_cents)


def _run_build_index(CardScanner, adapter) -> None:
    report = CardScanner.build_index(adapter)
    print(f"\nIndex built: {report.embedded}/{report.total} cards embedded "
          f"({report.skipped} skipped) in {report.duration_seconds:.0f}s")


def _get_market_price(product_id: int) -> int | None:
    """Look up latest market price in cents for a product_id. Returns None if unavailable.

    repo.get_card() and price_snapshots exist in the current codebase (used in api.py).
    The try/except catches edge cases: card not found, no snapshots, or any DB error.
    """
    from pokeassistant.database import get_engine, get_session_factory
    from pokeassistant.repositories.sqlalchemy_repo import SQLAlchemyRepository
    session = get_session_factory(get_engine())()
    try:
        repo = SQLAlchemyRepository(session)
        card = repo.get_card(product_id)
        if card and card.price_snapshots:
            return card.price_snapshots[-1].market_price_cents
        return None
    except Exception:
        return None  # price display is optional — never crash a successful scan
    finally:
        session.close()


def _print_result(result, warn_threshold: float, market_cents: int | None = None) -> None:
    top = result.top
    warn = " ⚠ low confidence" if top.confidence < warn_threshold else ""
    price_str = f"  market: ${market_cents / 100:.2f}\n" if market_cents else ""
    print(f"\n✓ {top.card.name} — {top.card.set_name} ({top.card.metadata.get('card_number', '?')})")
    print(f"  match:  {top.confidence:.0%} via {top.method}{warn}")
    print(f"{price_str}  time:   {result.scan_ms:.0f}ms")
    if result.alternatives:
        print("  alternatives:")
        for alt in result.alternatives:
            print(f"    · {alt.card.name} {alt.card.set_name}  {alt.confidence:.0%}")


def run_track(args: argparse.Namespace) -> None:
    # ... paste the entire existing main() body here, unchanged,
    # replacing references to `args.product_id` etc. (already correct)
    # This is all the existing scraper logic from the old main() function.
    raise NotImplementedError(
        "IMPLEMENTER: paste the full body of the OLD main() from cli.py here. "
        "Replace this line — do not leave it in."
    )
```

> **IMPORTANT — complete `run_track()` before running any tests:**
> Open the original `cli.py` in your editor (git diff will show the old `main()` body as deleted lines).
> Copy its entire body and paste it as the body of `run_track()`, replacing the `raise NotImplementedError(...)` line.
> The argument names (`args.product_id`, `args.scrape`, etc.) are identical — argparse produces the same
> attribute names regardless of subcommand. Do not skip this step or tests will fail with `NotImplementedError`.

- [ ] **Step 4b: Run tests to verify they pass**

```bash
pytest tests/test_cli.py -v
```
Expected: all `PASSED` including both old (migrated to `track`) and new (scan) tests

- [ ] **Step 5: Smoke test the CLI**

```bash
pokeassistant track --help
pokeassistant scan --help
```
Expected: both show valid help text with their respective flags

- [ ] **Step 6: Commit**

```bash
git add src/pokeassistant/cli.py tests/test_cli.py
git commit -m "feat(cli): refactor to subparsers — track + scan subcommands (v0.2.0 breaking)"
```

---

## Task 10: Full Test Suite + Final Cleanup

- [ ] **Step 1: Run full CI test suite (no integration tests)**

```bash
pytest tests/ -m "not integration" -v
```
Expected: all `PASSED`. If any fail, fix before proceeding.

- [ ] **Step 2: Verify vision extras install cleanly**

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu --dry-run
pip install -e '.[vision]' --dry-run
```
Expected: no dependency conflicts

- [ ] **Step 3: Run integration tests locally (requires ~235MB downloads on first run)**

```bash
pytest tests/ -m integration -v
```
Expected: all `PASSED`

- [ ] **Step 4: Add pytest.ini marker registration to pyproject.toml**

Add to `pyproject.toml` so `pytest -m 'not integration'` works without warnings:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
markers = [
    "integration: requires model weight downloads, skip in CI",
]
```

- [ ] **Step 5: Final commit**

```bash
git add pyproject.toml
git commit -m "chore: register integration pytest marker in pyproject.toml"
```

- [ ] **Step 6: Tag the release**

```bash
git tag v0.2.0
```
