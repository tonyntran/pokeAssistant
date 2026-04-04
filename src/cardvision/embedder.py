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
