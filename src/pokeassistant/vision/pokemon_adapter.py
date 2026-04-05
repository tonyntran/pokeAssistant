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
        Filters only by image_url IS NOT NULL — no product_type filter, per spec.
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
