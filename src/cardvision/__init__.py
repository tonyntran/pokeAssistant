"""cardvision — game-agnostic card scanning engine.

Submodules are imported explicitly to avoid loading heavy vision dependencies
(torch, opencv, easyocr) at package import time. Import directly from submodules:

    from cardvision.result import CardRecord, ScanResult
    from cardvision.exceptions import IndexNotBuiltError
    from cardvision.scanner import CardScanner
"""
