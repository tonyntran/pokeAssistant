"""PriceCharting scraper — graded card prices from pricecharting.com.

URL patterns:
  Search: https://www.pricecharting.com/search-products?type=prices&q={query}
  Card:   https://www.pricecharting.com/game/pokemon-{set-slug}/{card-slug}
"""

import re
from datetime import datetime
from typing import Optional
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from pokeassistant.models import GradedPrice, dollars_to_cents

_BASE = "https://www.pricecharting.com"

# Map full-prices table row labels to GradedPrice fields
_GRADE_MAP = {
    "ungraded": "ungraded_cents",
    "grade 7": "grade_7_cents",
    "grade 8": "grade_8_cents",
    "grade 9": "grade_9_cents",
    "grade 9.5": "grade_9_5_cents",
    "psa 10": "psa_10_cents",
    "bgs 10": "bgs_10_cents",
    "cgc 10": "cgc_10_cents",
    "sgc 10": "sgc_10_cents",
}


def build_search_url(query: str) -> str:
    """Build a PriceCharting search URL for the given query."""
    return f"{_BASE}/search-products?type=prices&q={quote_plus(query)}"


def _parse_price(text: str) -> Optional[int]:
    """Parse a dollar string like '$4,177.17' into cents. Returns None if unparseable."""
    text = text.strip()
    match = re.search(r"\$[\d,]+\.\d{2}", text)
    if not match:
        return None
    cleaned = match.group().replace("$", "").replace(",", "")
    return dollars_to_cents(cleaned)


def parse_graded_prices(html: str, product_id: int, url: str) -> GradedPrice:
    """Parse graded prices from a PriceCharting card page HTML.

    Extracts prices from the #full-prices table and the card name from #product_name.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Card name
    name_el = soup.find(id="product_name")
    card_name = name_el.get_text(strip=True) if name_el else "Unknown"

    # Parse full-prices table
    prices = {}
    table = soup.find(id="full-prices")
    if table:
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                grade_label = cells[0].get_text(strip=True).lower()
                price_text = cells[1].get_text(strip=True)
                field = _GRADE_MAP.get(grade_label)
                if field:
                    prices[field] = _parse_price(price_text)

    return GradedPrice(
        product_id=product_id,
        card_name=card_name,
        source="pricecharting",
        timestamp=datetime.now(),
        pricecharting_url=url,
        **prices,
    )


def search_card(query: str) -> Optional[str]:
    """Search PriceCharting for a card and return the card page URL.

    PriceCharting may redirect directly to a card page if there's an exact match,
    or show a search results page with links.

    Returns None if no results found.
    """
    url = build_search_url(query)
    resp = requests.get(url, allow_redirects=True)
    resp.raise_for_status()

    # If redirected to a card page (URL contains /game/), use that
    if "/game/" in resp.url:
        return resp.url

    # Otherwise parse search results for first link
    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find(id="games_table")
    if table:
        link = table.find("a", href=True)
        if link:
            href = link["href"]
            if href.startswith("/"):
                return f"{_BASE}{href}"
            return href

    return None


def fetch_graded_prices(card_name: str, product_id: int) -> Optional[GradedPrice]:
    """Search for a card on PriceCharting and fetch its graded prices.

    Args:
        card_name: Search query (e.g. "umbreon ex 161 prismatic evolutions")
        product_id: TCGPlayer product ID to associate with the result

    Returns:
        GradedPrice with all available grade prices, or None if card not found.
    """
    card_url = search_card(card_name)
    if not card_url:
        return None

    resp = requests.get(card_url)
    resp.raise_for_status()

    return parse_graded_prices(resp.text, product_id=product_id, url=card_url)
