# cardvision — Card Scanning Design Spec

**Date:** 2026-04-01  
**Status:** Approved  
**Version bump:** `0.1.0` → `0.2.0` (breaking CLI change — see §8)

---

## 1. Problem & Goal

Given a photo of a Pokemon TCG card, identify it from the local database and return the card name, set, confidence score, and current market price. No iOS app required — the full pipeline runs as a Python CLI command:

```bash
pokeassistant scan card.jpg
# → ✓ Charizard — Base Set (4/102)  |  99% via ocr  |  $420.00  |  43ms
```

The system must be modular enough that adding a second card game (e.g. Riftbound) requires writing one new adapter file, with zero changes to the core engine.

---

## 2. Prerequisite

`pokeassistant scan --build-index` downloads card images from URLs already stored in the `products.image_url` column and embeds them into a FAISS index. This means cards must already be in the database with `image_url` populated before the index can be built.

**Full coverage** requires the upcoming `--import-all-sets` feature (separate PR, Phase 1). In the meantime, a partial index built from already-tracked sets is valid and useful.

---

## 3. Architecture

Two packages, one dependency direction:

```
src/
  cardvision/                    # game-agnostic CV engine (new)
    adapter.py                   # GameAdapter Protocol
    detector.py                  # OpenCV card detection + perspective warp
    ocr.py                       # EasyOCR text extraction
    embedder.py                  # DINOv2 ViT-S/14 → embedding vector
    index.py                     # FAISS index build + query
    scanner.py                   # two-path orchestrator (entry point)
    result.py                    # ScanResult, ScanMatch, CardRecord dataclasses

  pokeassistant/
    vision/                      # Pokemon-specific adapter (new sub-package)
      __init__.py
      pokemon_adapter.py         # implements GameAdapter Protocol
    cli.py                       # refactored to subparsers, adds scan subcommand
    # all other files unchanged

data/                            # git-ignored, generated
  pokemon.index                  # FAISS binary (~6MB for 15,000 cards)
  pokemon_cards.json             # card_id → CardRecord metadata (~2MB)

tests/
  test_cardvision/
    test_detector.py
    test_ocr.py
    test_embedder.py
    test_index.py
    test_scanner.py
    fixtures/
      clean_card.jpg             # clear scan — OCR + embed both succeed
      angled_card.jpg            # perspective skewed — tests warp
      worn_card.jpg              # damaged — tests embedding fallback
      blurry_card.jpg            # blur causes OCR garbage — tests silent fallthrough
      glare_card.jpg             # foil glare blocks OCR — tests silent fallthrough
```

**Dependency rule:** `cardvision` never imports from `pokeassistant`. The adapter in `pokeassistant/vision/` imports from both. This boundary makes the engine reusable for any future game.

---

## 4. Scan Pipeline

Two paths — OCR first, embedding fallback:

```
Image path
  ↓
CardDetector.detect_and_warp()     OpenCV: find card edges, perspective-correct to flat rectangle
  ↓
── OCR PATH (fast, primary) ──────────────────────────────────────────
CardDetector.crop_name_region()    top 15% of card
CardDetector.crop_number_region()  bottom-right corner
CardOCR.extract()                  EasyOCR → OCRExtract{name, set_number, confidence}

IF ocr.name AND ocr.set_number:
    adapter.lookup_by_text(name, set_number) → list[CardRecord]
    IF exactly 1 result:
        return ScanResult(method="ocr", confidence=ocr.confidence)
    # 0 or 2+ results (ambiguous — e.g. Shadowless vs Unlimited) → fall through

── EMBEDDING PATH (fallback) ──────────────────────────────────────────
CardEmbedder.embed()               DINOv2 ViT-S/14 → 384-d L2-normalized vector
CardIndex.query(top_k=3)           FAISS cosine search → [(CardRecord, float)]
return ScanResult(method="embedding", confidence=matches[0][1])
```

The fallthrough is always silent — no error raised, no user-visible message. The result's `method` field tells you which path was used.

---

## 5. Data Types (`result.py`)

```python
@dataclass
class CardRecord:
    card_id: str           # str(product_id) from DB
    name: str
    set_name: str
    image_url: str
    metadata: dict         # card_number, rarity, etc. — game-specific extras

@dataclass
class ScanMatch:
    card: CardRecord
    confidence: float      # 0.0–1.0
    method: Literal["ocr", "embedding"]

@dataclass
class ScanResult:
    top: ScanMatch
    alternatives: list[ScanMatch]   # next-best matches, embedding path only
    scan_ms: float
```

---

## 6. GameAdapter Protocol (`adapter.py`)

```python
@runtime_checkable
class GameAdapter(Protocol):
    game_id: str           # "pokemon", "riftbound", etc.

    def get_card_catalog(self) -> list[CardRecord]:
        """All cards with image_url — used by CardIndex.build()."""
        ...

    def get_index_paths(self) -> tuple[Path, Path]:
        """Returns (faiss_index_path, metadata_json_path)."""
        ...

    def lookup_by_text(self, name: str, set_number: str) -> list[CardRecord]:
        """OCR text → candidate cards. Returns multiple if ambiguous."""
        ...
```

Adding Riftbound = one new file implementing this Protocol. No changes to `cardvision/`.

---

## 7. Component Interfaces

### CardDetector (`detector.py`)
```python
class CardDetector:
    def detect_and_warp(self, image_path: Path) -> Image: ...
    def crop_name_region(self, card: Image) -> Image: ...      # top 15%
    def crop_number_region(self, card: Image) -> Image: ...    # bottom-right corner
```

### CardOCR (`ocr.py`)
```python
@dataclass
class OCRExtract:
    name: str | None
    set_number: str | None     # e.g. "4/102"
    confidence: float

class CardOCR:
    def extract(self, card: Image) -> OCRExtract: ...
```

### CardEmbedder (`embedder.py`)
```python
class CardEmbedder:
    def __init__(self, model: str = "dinov2_vits14"): ...
    def embed(self, image: Path | Image) -> np.ndarray: ...         # shape (384,), L2-normalized
    def embed_batch(self, images: list[Path], batch_size: int = 32) -> np.ndarray: ...
```

DINOv2 ViT-S/14 chosen over EfficientNet-B3 because it produces richer semantic features for image retrieval without any fine-tuning. The `model` parameter is swappable for future upgrades.

### CardIndex (`index.py`)
```python
@dataclass
class BuildReport:
    total: int
    embedded: int
    skipped: int               # failed downloads or embed errors — warned, never aborted
    duration_seconds: float

class CardIndex:
    def build(
        self,
        catalog: list[CardRecord],
        embedder: CardEmbedder,
        index_path: Path,
        meta_path: Path,
        request_delay: float = 0.1,    # seconds between image downloads
        max_retries: int = 3,          # exponential backoff on 429/5xx
    ) -> BuildReport: ...

    def load(self, index_path: Path, meta_path: Path) -> None: ...
    def query(self, embedding: np.ndarray, top_k: int = 5) -> list[tuple[CardRecord, float]]: ...

    @property
    def is_loaded(self) -> bool: ...
```

**Build behavior:** images are downloaded to memory only — never written to disk. The loop uses `tqdm` for progress display and exponential backoff for rate limiting. A single card failure logs a warning and continues; the build never aborts mid-run.

### CardScanner (`scanner.py`) — the only class callers touch
```python
OCR_CONFIDENCE_THRESHOLD = 0.9

class CardScanner:
    def __init__(self, adapter: GameAdapter): ...    # loads index from disk
    def scan(self, image_path: Path, top_k: int = 3) -> ScanResult: ...

    @classmethod
    def build_index(cls, adapter: GameAdapter) -> BuildReport: ...
```

### PokemonAdapter (`pokeassistant/vision/pokemon_adapter.py`)
```python
class PokemonAdapter:
    game_id = "pokemon"

    def get_card_catalog(self) -> list[CardRecord]:
        # Query Product table WHERE image_url IS NOT NULL
        # Returns CardRecord with metadata={card_number, rarity}

    def get_index_paths(self) -> tuple[Path, Path]:
        # Returns (data/pokemon.index, data/pokemon_cards.json)

    def lookup_by_text(self, name: str, set_number: str) -> list[CardRecord]:
        # Reuses existing repo.search() — no new DB code
```

---

## 8. CLI Changes (Breaking — v0.2.0)

The existing flat-flag CLI is refactored to subparsers.

**Breaking change:** `pokeassistant --product-id X --tcgcsv` no longer works. Users must update to `pokeassistant track --product-id X --tcgcsv`. Document in `CHANGELOG.md`.

```
pokeassistant track --product-id 3816 --tcgcsv    # existing behavior, new subcommand name
pokeassistant scan card.jpg                        # new: identify a card
pokeassistant scan --build-index                   # new: build FAISS index from DB
pokeassistant scan card.jpg --top 5                # show top 5 alternatives
```

**Lazy import pattern:** `cardvision` and `torch` are only imported when the `scan` subcommand is invoked. `pokeassistant track ...` starts instantly with no ML library overhead.

**First-run UX:** if `pokemon.index` doesn't exist, `run_scan()` catches `IndexNotBuiltError` and prompts:
```
No card index found.
Build it now? This downloads card images and takes ~5 min. [y/N]
```

**Import error UX:** if `[vision]` extras aren't installed:
```
Vision dependencies not installed.
Run: pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
Then: pip install 'pokeassistant[vision]'
```

---

## 9. Dependencies

Added to `pyproject.toml` as optional:

```toml
[project.optional-dependencies]
vision = [
    "torch>=2.0",
    "torchvision>=0.15",
    "faiss-cpu>=1.7",
    "opencv-python-headless>=4.8",
    "easyocr>=1.7",
    "Pillow>=10.0",
]
```

**Install order matters** — standard `pip install torch` bundles CUDA and exceeds 2GB. Document CPU-only install in README:

```bash
# Step 1: CPU-only PyTorch (~250MB instead of 2GB+)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Step 2: vision extras
pip install 'pokeassistant[vision]'
```

---

## 10. Error Handling

| Error | Trigger | User message |
|-------|---------|--------------|
| `IndexNotBuiltError` | `pokemon.index` not found on scanner init | `"Run: pokeassistant scan --build-index"` (with interactive prompt) |
| `CardNotDetectedError` | OpenCV finds no card-shaped rectangle | `"No card found. Ensure card fills frame."` |
| `EmptyCatalogError` | DB has no products with `image_url` | `"Import cards first: pokeassistant track --tcgcsv"` |
| `ImageLoadError` | Pillow receives corrupted file or wrong format | `"Could not read image: {path}. Check the file is a valid JPG/PNG."` |
| `CameraInitializationError` | `cv2.VideoCapture(0)` returns no frames | `"Could not access camera."` (stubbed, reserved for webcam mode) |
| OCR returns None | Foil glare, blur, worn text | Silent fallthrough to embedding path |
| Ambiguous OCR match | `lookup_by_text()` returns 2+ cards | Silent fallthrough to embedding path |
| Low embedding confidence | Score < 0.70 | Result returned with `⚠` flag + top-3 alternatives shown |

---

## 11. Testing Strategy

All scanner tests use a mocked `GameAdapter` — no real DB or model downloads needed in CI. Model-dependent tests (embedder, OCR, detector) run against fixture images.

| File | What it tests |
|------|--------------|
| `test_embedder.py` | DINOv2 output shape `(384,)`, dtype `float32`, L2 norm ≈ 1.0; same image → cosine similarity > 0.99 |
| `test_index.py` | Build index from 3 synthetic CardRecords + fake embeddings; query returns correct card as top result |
| `test_ocr.py` | `clean_card.jpg` → non-empty name extracted; `blurry_card.jpg` + `glare_card.jpg` → OCRExtract with None fields |
| `test_detector.py` | `angled_card.jpg` → warped output has expected aspect ratio |
| `test_scanner.py` | 4 branching paths: OCR success → OCR result; ambiguous OCR → embedding; OCR None → embedding; low embedding confidence → warning flag |

---

## 12. Known Limitations (v1)

**1st Edition Stamp:** Both OCR and embedding paths may fail to distinguish 1st Edition from Unlimited Base Set. The stamp is tiny and often faded. CLI emits: `⚠ 1st Edition variant possible — verify manually`

**Reverse Holo / Foil variants:** Same name, same set number as the base version. Camera struggles with holographic surfaces. Could be a $0.50 card or a $15.00 Reverse Holo. CLI emits: `⚠ Holo variant possible — verify manually`

Both share the same pattern: same `card_number`, multiple `product_id`s, difference is surface finish not artwork. A dedicated surface-finish classifier is a natural v2 addition.

---

## 13. Out of Scope (future PRs)

| Feature | Notes |
|---------|-------|
| `--import-all-sets` | Phase 1 PR — bulk TCGcsv import, prerequisite for full index coverage |
| `POST /api/scan` | FastAPI endpoint for frontend image upload |
| Webcam live scan | `cv2.VideoCapture(0)` real-time loop |
| Fine-tuned model / ArcFace | Phase 2 accuracy upgrade; swap model in `embedder.py` |
| Riftbound adapter | One new file implementing `GameAdapter` Protocol |
