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
_NUMBER_REGION_LEFT = 0.0   # scan full width; OCR regex finds the pattern wherever it is

# Minimum contour area to be considered a card candidate
_MIN_CARD_AREA_PX2 = 5_000   # ~71×71px minimum; rejects noise contours below card size


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
            # Use bounding-rect area for size check: contourArea is unreliable
            # for edge-traced (ring) contours where the enclosed area is ~0.
            _, _, bw, bh = cv2.boundingRect(cnt)
            if bw * bh <= _MIN_CARD_AREA_PX2:
                continue
            # Simplify via convex hull before polygon approximation so that
            # jagged edge pixels from anti-aliased/thick borders collapse cleanly.
            hull = cv2.convexHull(cnt)
            peri = cv2.arcLength(hull, True)
            approx = cv2.approxPolyDP(hull, 0.02 * peri, True)
            if len(approx) == 4:
                card_corners = approx.reshape(4, 2).astype("float32")
                break
            # Rotated cards may still produce 5–8 hull points; fall back to
            # the minimum bounding rectangle which always gives exactly 4 corners.
            if 4 < len(approx) <= 8:
                rect = cv2.minAreaRect(hull)
                card_corners = cv2.boxPoints(rect).astype("float32")
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
    """Order corners as: top-left, top-right, bottom-right, bottom-left.

    Uses centroid angles rather than sum/diff to handle all rotation angles
    correctly (the sum/diff method breaks at exactly 45°).
    """
    center = pts.mean(axis=0)
    angles = np.arctan2(pts[:, 1] - center[1], pts[:, 0] - center[0])
    # Sort CCW starting from rightmost point
    order = np.argsort(angles)
    pts_ccw = pts[order]
    # Rotate so top-left (minimum x+y) is first
    s = pts_ccw.sum(axis=1)
    start = int(np.argmin(s))
    return np.roll(pts_ccw, -start, axis=0)
