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
