import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "pokeassistant.db"

# TCGPlayer product URL template
TCGPLAYER_PRODUCT_URL = "https://www.tcgplayer.com/product/{product_id}"

# TCGCSV base URL (category 3 = Pokemon)
TCGCSV_BASE_URL = "https://tcgcsv.com/3"


def get_db_path() -> Path:
    return Path(os.environ.get("POKEASSISTANT_DB_PATH", str(DEFAULT_DB_PATH)))


def get_headless() -> bool:
    return os.environ.get("POKEASSISTANT_HEADLESS", "true").lower() == "true"


def get_min_delay() -> float:
    return float(os.environ.get("POKEASSISTANT_MIN_DELAY", "2"))


def get_max_delay() -> float:
    return float(os.environ.get("POKEASSISTANT_MAX_DELAY", "5"))
