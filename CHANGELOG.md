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
