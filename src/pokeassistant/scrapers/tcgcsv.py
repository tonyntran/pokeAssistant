"""TCGCSV fetcher — free daily TCGPlayer price snapshots (no browser needed).

Endpoints (category 3 = Pokemon):
  Groups:   https://tcgcsv.com/tcgplayer/3/groups
  Products: https://tcgcsv.com/tcgplayer/3/{group_id}/products
  Prices:   https://tcgcsv.com/tcgplayer/3/{group_id}/prices
"""

from datetime import datetime
from typing import Optional

import requests

from pokeassistant.config import TCGCSV_BASE_URL
from pokeassistant.models import PriceSnapshot, Product, dollars_to_cents

# Base URL is "https://tcgcsv.com/3" from config, but the real API uses /tcgplayer/3
_BASE = "https://tcgcsv.com/tcgplayer/3"


def fetch_groups() -> list[dict]:
    """Fetch all Pokemon TCG groups (sets) from TCGCSV."""
    resp = requests.get(f"{_BASE}/groups")
    resp.raise_for_status()
    return resp.json()["results"]


def find_group_by_name(search: str) -> Optional[dict]:
    """Find a group whose name contains the search string (case-insensitive)."""
    groups = fetch_groups()
    search_lower = search.lower()
    for group in groups:
        if search_lower in group["name"].lower():
            return group
    return None


def fetch_products(group_id: int, as_models: bool = False) -> list:
    """Fetch all products for a group.

    If as_models=True, returns list[Product]. Otherwise returns raw dicts.
    """
    resp = requests.get(f"{_BASE}/{group_id}/products")
    resp.raise_for_status()
    results = resp.json()["results"]
    if not as_models:
        return results
    return [
        Product(
            product_id=p["productId"],
            name=p["name"],
            category="Pokemon",
            group_name=None,
            url=p.get("url"),
        )
        for p in results
    ]


def fetch_prices(group_id: int) -> list[dict]:
    """Fetch all price data for a group."""
    resp = requests.get(f"{_BASE}/{group_id}/prices")
    resp.raise_for_status()
    return resp.json()["results"]


def get_price_snapshot_for_product(
    group_id: int, product_id: int
) -> Optional[PriceSnapshot]:
    """Fetch prices for a group and return a PriceSnapshot for the given product.

    Returns None if product not found in the price data.
    """
    prices = fetch_prices(group_id)
    for price in prices:
        if price["productId"] == product_id:
            return PriceSnapshot(
                product_id=product_id,
                timestamp=datetime.now(),
                source="tcgcsv",
                low_price_cents=dollars_to_cents(price.get("lowPrice")),
                market_price_cents=dollars_to_cents(price.get("marketPrice")),
                high_price_cents=dollars_to_cents(price.get("highPrice")),
                listing_count=None,  # TCGCSV doesn't provide listing count
            )
    return None
