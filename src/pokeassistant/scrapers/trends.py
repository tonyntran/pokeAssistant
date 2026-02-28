"""Google Trends integration via pytrends.

Fetches interest_over_time data for Pokemon TCG keywords.
pytrends is an unofficial API and may be rate-limited or unstable,
so all calls are wrapped in try/except and the module is optional.
"""

import time
from datetime import date
from typing import Optional

import pandas as pd

from pokeassistant.models import TrendDataPoint

# Delay between pytrends calls to avoid rate limiting
RATE_LIMIT_DELAY = 2.0


def parse_interest_over_time(
    df: pd.DataFrame,
    keyword: str,
    skip_partial: bool = False,
) -> list[TrendDataPoint]:
    """Convert a pytrends interest_over_time DataFrame into TrendDataPoint objects."""
    if df.empty or keyword not in df.columns:
        return []

    points = []
    for idx, row in df.iterrows():
        if skip_partial and row.get("isPartial", False):
            continue
        points.append(TrendDataPoint(
            keyword=keyword,
            date=idx.date() if hasattr(idx, "date") else date.fromisoformat(str(idx)),
            interest=int(row[keyword]),
            source="google_trends",
        ))
    return points


def fetch_trends(
    keywords: list[str],
    timeframe: str = "today 3-m",
    skip_partial: bool = False,
) -> list[TrendDataPoint]:
    """Fetch Google Trends interest_over_time for the given keywords.

    Returns a list of TrendDataPoint objects, or an empty list on failure.
    Keywords are batched in groups of 5 (pytrends limit).
    """
    try:
        from pytrends.request import TrendReq
    except ImportError:
        return []

    all_points = []

    try:
        pytrends = TrendReq(hl="en-US", tz=360)

        # pytrends supports up to 5 keywords per request
        for i in range(0, len(keywords), 5):
            batch = keywords[i : i + 5]
            pytrends.build_payload(batch, timeframe=timeframe)
            df = pytrends.interest_over_time()

            for kw in batch:
                points = parse_interest_over_time(df, kw, skip_partial=skip_partial)
                all_points.extend(points)

            if i + 5 < len(keywords):
                time.sleep(RATE_LIMIT_DELAY)

    except Exception:
        return all_points if all_points else []

    return all_points
