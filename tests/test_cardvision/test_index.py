"""Unit tests for CardIndex — runs in CI using synthetic embeddings (no model downloads)."""
import json
import numpy as np
import pytest
from pathlib import Path

from cardvision.index import CardIndex
from cardvision.result import CardRecord
from cardvision.exceptions import EmptyCatalogError, IndexNotBuiltError


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


def test_query_raises_when_index_not_loaded():
    index = CardIndex()
    vec = make_fake_embeddings(1)[0]
    with pytest.raises(IndexNotBuiltError):
        index.query(vec, top_k=1)


def test_build_from_embeddings_raises_on_empty_catalog(tmp_path):
    index = CardIndex()
    with pytest.raises(EmptyCatalogError):
        index.build_from_embeddings(
            [], np.empty((0, 384), dtype="float32"),
            tmp_path / "x.index", tmp_path / "x.json"
        )


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


def test_query_raises_when_index_not_loaded():
    index = CardIndex()
    vec = make_fake_embeddings(1)[0]
    with pytest.raises(IndexNotBuiltError):
        index.query(vec, top_k=1)


def test_build_from_embeddings_raises_on_empty_catalog(tmp_path):
    index = CardIndex()
    with pytest.raises(EmptyCatalogError):
        index.build_from_embeddings(
            [], np.empty((0, 384), dtype="float32"),
            tmp_path / "x.index", tmp_path / "x.json"
        )
