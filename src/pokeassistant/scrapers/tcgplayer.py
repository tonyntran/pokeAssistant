"""TCGPlayer scraper using Playwright for headless browsing.

Intercepts XHR API calls made by the TCGPlayer SPA to extract:
- Product details (name, set, category)
- Current market/low/high prices
- Listing count
- Price history buckets (daily market price + sales volume)

Key API endpoints discovered via recon:
- mp-search-api.tcgplayer.com/v2/product/{id}/details
- mp-search-api.tcgplayer.com/v1/product/{id}/listings
- mpgateway.tcgplayer.com/v1/pricepoints/marketprice/skus/search
- infinite-api.tcgplayer.com/price/history/{id}/detailed?range=quarter
"""

import asyncio
import random
from datetime import datetime, date
from typing import Optional

from pokeassistant.config import get_headless, get_min_delay, get_max_delay
from pokeassistant.models import PriceSnapshot, SaleRecord, Product, dollars_to_cents

PRODUCT_URL = "https://www.tcgplayer.com/product/{product_id}"


# --- Parsers (pure functions, no browser needed) ---


def parse_product_details(data: dict) -> Product:
    """Parse the /v2/product/{id}/details response into a Product."""
    product_id = int(data["productId"])
    category = data.get("productLineUrlName", "Pokemon")
    # Classify as card (single) or sealed based on category keywords
    cat_lower = (data.get("customAttributes", {}).get("productTypeName", "") or "").lower()
    if not cat_lower:
        cat_lower = (data.get("productTypeName", "") or "").lower()
    if "single" in cat_lower or "card" in cat_lower:
        product_type = "card"
    elif "sealed" in cat_lower or "box" in cat_lower or "pack" in cat_lower or "bundle" in cat_lower:
        product_type = "sealed"
    else:
        product_type = None
    return Product(
        product_id=product_id,
        name=data.get("productName", data.get("productUrlName", "")),
        category=category,
        group_name=data.get("setName"),
        url=PRODUCT_URL.format(product_id=product_id),
        product_type=product_type,
    )


def parse_listings_count(data: dict) -> int:
    """Parse the /v1/product/{id}/listings response to get total listing count."""
    results = data.get("results", [])
    if not results:
        return 0
    return int(results[0].get("totalResults", 0))


def parse_market_price(data: list) -> Optional[dict]:
    """Parse the /v1/pricepoints/marketprice/skus/search response.

    Returns dict with market_price_cents, low_price_cents, high_price_cents.
    """
    if not data:
        return None
    entry = data[0]
    return {
        "market_price_cents": dollars_to_cents(entry.get("marketPrice")),
        "low_price_cents": dollars_to_cents(entry.get("lowestPrice")),
        "high_price_cents": dollars_to_cents(entry.get("highestPrice")),
    }


def build_snapshot_from_details(
    details: dict, listings: dict, market: list
) -> PriceSnapshot:
    """Build a PriceSnapshot from the three API responses."""
    product_id = int(details["productId"])
    listing_count = parse_listings_count(listings)
    prices = parse_market_price(market)

    return PriceSnapshot(
        product_id=product_id,
        timestamp=datetime.now(),
        source="tcgplayer",
        low_price_cents=prices["low_price_cents"] if prices else None,
        market_price_cents=prices["market_price_cents"] if prices else None,
        high_price_cents=prices["high_price_cents"] if prices else None,
        listing_count=listing_count,
    )


def parse_price_history(data: dict) -> list[dict]:
    """Parse the /price/history/{id}/detailed response into bucket dicts.

    Each bucket has: date, market_price_cents, quantity_sold, low/high sale prices.
    """
    results = data.get("result", [])
    if not results:
        return []
    buckets = results[0].get("buckets", [])
    parsed = []
    for b in buckets:
        # API uses "bucketStartDate" in live responses, "bucket" in some versions
        bucket_date = b.get("bucketStartDate") or b.get("bucket")
        parsed.append({
            "date": bucket_date,
            "market_price_cents": dollars_to_cents(b.get("marketPrice")),
            "quantity_sold": int(b.get("quantitySold", 0)),
            "low_sale_cents": dollars_to_cents(b.get("lowSalePrice")),
            "high_sale_cents": dollars_to_cents(b.get("highSalePrice")),
        })
    return parsed


def build_sale_records_from_history(
    data: dict, product_id: int
) -> list[SaleRecord]:
    """Build SaleRecord objects from price history buckets.

    Each bucket represents a day's aggregate sales data. We store the market price
    and quantity as a single record per day.
    """
    results = data.get("result", [])
    if not results:
        return []

    sku_data = results[0]
    condition = sku_data.get("condition")
    variant = sku_data.get("variant")
    records = []

    for bucket in sku_data.get("buckets", []):
        bucket_date = bucket.get("bucketStartDate") or bucket.get("bucket")
        sale_date = date.fromisoformat(bucket_date)
        market_price_cents = dollars_to_cents(bucket.get("marketPrice"))
        quantity = int(bucket.get("quantitySold", 0))

        if market_price_cents is not None and quantity > 0:
            records.append(SaleRecord(
                product_id=product_id,
                sale_date=sale_date,
                condition=condition,
                variant=variant,
                price_cents=market_price_cents,
                quantity=quantity,
                source="tcgplayer",
            ))

    return records


# --- Browser scraper ---


async def scrape_product(product_id: int, headless: bool = True) -> dict:
    """Scrape a TCGPlayer product page using Playwright.

    Returns a dict with:
        product: Product
        snapshot: PriceSnapshot
        sale_records: list[SaleRecord]
        price_history_raw: dict
    """
    from playwright.async_api import async_playwright

    captured = {}

    async def on_response(response):
        url = response.url
        ct = response.headers.get("content-type", "")
        if "json" not in ct:
            return
        try:
            if f"v2/product/{product_id}/details" in url:
                captured["details"] = await response.json()
            elif f"v1/product/{product_id}/listings" in url and "listings" not in captured:
                captured["listings"] = await response.json()
            elif "pricepoints/marketprice/skus/search" in url:
                captured["market"] = await response.json()
            elif f"price/history/{product_id}" in url:
                captured["history"] = await response.json()
        except Exception:
            pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()
        page.on("response", on_response)

        url = PRODUCT_URL.format(product_id=product_id)
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)

        # Wait for the product details XHR specifically, with a fallback timeout
        for _ in range(20):
            if "details" in captured:
                break
            await page.wait_for_timeout(500)

        # Scroll down to trigger lazy-loaded XHRs (listings, price history)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
        await page.wait_for_timeout(2000)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

        # Wait for remaining XHRs with randomized delay
        delay = random.uniform(get_min_delay(), get_max_delay())
        await page.wait_for_timeout(int(delay * 1000))

        # Extra time for price history / market price endpoints
        for _ in range(10):
            if "history" in captured or "market" in captured:
                break
            await page.wait_for_timeout(500)

        await browser.close()

    # Build results from captured data
    result = {"product": None, "snapshot": None, "sale_records": [], "price_history_raw": None}

    if "details" in captured:
        result["product"] = parse_product_details(captured["details"])

        if "listings" in captured and "market" in captured:
            result["snapshot"] = build_snapshot_from_details(
                captured["details"], captured["listings"], captured["market"]
            )
        elif "details" in captured:
            # Fallback: build snapshot from details alone
            result["snapshot"] = PriceSnapshot(
                product_id=product_id,
                timestamp=datetime.now(),
                source="tcgplayer",
                market_price_cents=dollars_to_cents(captured["details"].get("marketPrice")),
                low_price_cents=dollars_to_cents(captured["details"].get("lowestPrice")),
                listing_count=int(captured["details"].get("totalListings", 0)),
            )

    if "history" in captured:
        result["price_history_raw"] = captured["history"]
        result["sale_records"] = build_sale_records_from_history(
            captured["history"], product_id
        )

    return result
