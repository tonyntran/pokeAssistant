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


class OCRError(CardVisionError):
    """Raised when EasyOCR fails to process a region."""
