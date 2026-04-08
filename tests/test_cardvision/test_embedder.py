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
    assert batch.dtype == np.float32
    # Each row should be L2-normalized
    norms = np.linalg.norm(batch, axis=1)
    assert np.allclose(norms, 1.0, atol=1e-5)


@pytest.mark.integration
def test_embed_accepts_pil_image():
    img = Image.new("RGB", (400, 560), color=(80, 120, 160))
    embedder = CardEmbedder()
    vec = embedder.embed(img)
    assert vec.shape == (384,)
    assert vec.dtype == np.float32
