"""Tests for PokemonAdapter — uses in-memory SQLite (no network or FAISS)."""
import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from pokeassistant.models import Base, Product
from pokeassistant.database import get_session_factory, reset_engine
from pokeassistant.vision import PokemonAdapter
from cardvision.adapter import GameAdapter
from cardvision.result import CardRecord


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Use a fresh in-memory SQLite DB and reset singletons after each test."""
    db_url = "sqlite:///:memory:"
    monkeypatch.setenv("POKEASSISTANT_DB", db_url)
    reset_engine()
    from pokeassistant.database import get_engine
    engine = get_engine(db_url)
    Base.metadata.create_all(engine)
    yield engine
    reset_engine()


@pytest.fixture
def session(isolated_db):
    with Session(isolated_db) as s:
        yield s


@pytest.fixture
def adapter():
    return PokemonAdapter()


def test_satisfies_game_adapter_protocol(adapter):
    assert isinstance(adapter, GameAdapter), "PokemonAdapter must satisfy GameAdapter Protocol"


def test_game_id_is_pokemon(adapter):
    assert adapter.game_id == "pokemon"


def test_get_index_paths_returns_correct_files(adapter, tmp_path, monkeypatch):
    monkeypatch.setenv("POKEASSISTANT_DATA_DIR", str(tmp_path))
    from pokeassistant.config import get_data_dir
    # Force re-evaluation
    idx_path, meta_path = adapter.get_index_paths()
    assert idx_path.name == "pokemon.index"
    assert meta_path.name == "pokemon_cards.json"


def test_get_card_catalog_returns_only_products_with_image_url(session, adapter):
    session.add(Product(product_id=1, name="Charizard", image_url="http://example.com/1.jpg", card_number="4/102"))
    session.add(Product(product_id=2, name="Pikachu", image_url=None, card_number="58/102"))
    session.commit()

    catalog = adapter.get_card_catalog()
    assert len(catalog) == 1
    assert catalog[0].name == "Charizard"
    assert catalog[0].image_url == "http://example.com/1.jpg"


def test_get_card_catalog_returns_card_records(session, adapter):
    session.add(Product(product_id=99, name="Blastoise", image_url="http://example.com/2.jpg",
                        group_name="Base Set", card_number="2/102", rarity="Holo Rare"))
    session.commit()

    catalog = adapter.get_card_catalog()
    assert len(catalog) == 1
    rec = catalog[0]
    assert isinstance(rec, CardRecord)
    assert rec.card_id == "99"
    assert rec.set_name == "Base Set"
    assert rec.metadata["card_number"] == "2/102"
    assert rec.metadata["rarity"] == "Holo Rare"


def test_lookup_by_text_returns_matching_card(session, adapter):
    session.add(Product(product_id=10, name="Charizard", card_number="4/102",
                        image_url="http://example.com/char.jpg"))
    session.commit()

    results = adapter.lookup_by_text("Charizard", "4/102")
    assert len(results) == 1
    assert results[0].card_id == "10"


def test_lookup_by_text_returns_empty_for_no_match(adapter):
    results = adapter.lookup_by_text("Nonexistent", "999/999")
    assert results == []


def test_lookup_by_text_returns_multiple_for_ambiguous(session, adapter):
    session.add(Product(product_id=1, name="Charizard", card_number="4/102",
                        image_url="http://example.com/1.jpg", group_name="Base Set"))
    session.add(Product(product_id=2, name="Charizard", card_number="4/102",
                        image_url="http://example.com/2.jpg", group_name="Base Set Shadowless"))
    session.commit()

    results = adapter.lookup_by_text("Charizard", "4/102")
    assert len(results) == 2
    names = {r.set_name for r in results}
    assert "Base Set" in names
    assert "Base Set Shadowless" in names
