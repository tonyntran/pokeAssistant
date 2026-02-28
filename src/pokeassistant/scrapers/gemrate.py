"""GemRate scraper — PSA/BGS/CGC/SGC population reports from gemrate.com.

API endpoints:
  Search: POST https://www.gemrate.com/universal-search-query  {"query": "..."}
  Details: GET https://www.gemrate.com/card-details?gemrate_id={id}
           (requires session cookie + X-Card-Details-Token JWT)

Real API shape (population_data[]):
  - grader: "psa" | "beckett" | "sgc" | "cgc"
  - grades: {"g1": N, "g2": N, ..., "g10": N}  (PSA uses "auth" too)
  - halves: {"g1_5": N, ..., "g9_5": N} or None
  - BGS grades include "g10b" (Black Label) and "g10p" (Pristine)
  - CGC grades include "g10pristine" and "g10perfect"
"""

import re
from datetime import datetime
from typing import Optional

import requests

from pokeassistant.models import PopulationReport

_BASE = "https://www.gemrate.com"


def _get_session_and_token() -> tuple[requests.Session, str]:
    """Fetch the GemRate search page and extract the JWT token.

    The token is embedded in the page HTML as a JWT (eyJ...) and is required
    for the card-details API.
    """
    session = requests.Session()
    resp = session.get(f"{_BASE}/universal-search")
    resp.raise_for_status()

    # Extract JWT token from page HTML
    match = re.search(r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+", resp.text)
    token = match.group() if match else ""
    return session, token


def parse_search_results(data: list[dict]) -> list[dict]:
    """Parse GemRate search response into a list of result dicts."""
    return data


def _find_grader(population_data: list[dict], grader_name: str) -> Optional[dict]:
    """Find a grading company's data in the population_data list."""
    for entry in population_data:
        if entry.get("grader", "").lower() == grader_name.lower():
            return entry
    return None


def _get_grade(entry: Optional[dict], key: str) -> Optional[int]:
    """Safely get a grade count from a grader entry's grades dict."""
    if entry is None:
        return None
    grades = entry.get("grades") or {}
    val = grades.get(key)
    return val if val is not None else None


def _get_half(entry: Optional[dict], key: str) -> Optional[int]:
    """Safely get a half-grade count from a grader entry's halves dict."""
    if entry is None:
        return None
    halves = entry.get("halves")
    if halves is None:
        return None
    val = halves.get(key)
    return val if val is not None else None


def parse_population(data: dict, card_name: str, gemrate_id: str) -> PopulationReport:
    """Parse GemRate card-details JSON into a PopulationReport.

    Extracts per-grader counts for PSA, BGS (Beckett), and CGC.
    Grade keys use "g10", "g9" format (not "10", "9").
    """
    pop_data = data.get("population_data", [])

    # PSA — grades use g10, g9, g8
    psa = _find_grader(pop_data, "psa")
    psa_10 = _get_grade(psa, "g10")
    psa_9 = _get_grade(psa, "g9")
    psa_8 = _get_grade(psa, "g8")
    psa_gem_rate = psa.get("card_gem_rate") if psa else None
    # Convert to float (API may return string) and ratio to percentage
    if psa_gem_rate is not None:
        psa_gem_rate = float(psa_gem_rate)
        if psa_gem_rate < 1:
            psa_gem_rate = round(psa_gem_rate * 100, 2)

    # BGS (Beckett) — g9_5 in halves, g10b = Black Label, g10p = Pristine (both are "10")
    bgs = _find_grader(pop_data, "beckett")
    bgs_10_base = _get_grade(bgs, "g10") or 0
    bgs_10_black = _get_grade(bgs, "g10b") or 0
    bgs_10_pristine = _get_grade(bgs, "g10p") or 0
    bgs_10 = (bgs_10_base + bgs_10_black + bgs_10_pristine) if bgs else None
    bgs_9_5 = _get_half(bgs, "g9_5")

    # CGC — g10pristine and g10perfect are separate from g10
    cgc = _find_grader(pop_data, "cgc")
    cgc_10_base = _get_grade(cgc, "g10") or 0
    cgc_10_pristine = _get_grade(cgc, "g10pristine") or 0
    cgc_10_perfect = _get_grade(cgc, "g10perfect") or 0
    cgc_10 = (cgc_10_base + cgc_10_pristine + cgc_10_perfect) if cgc else None
    cgc_9_5 = _get_half(cgc, "g9_5")

    return PopulationReport(
        card_name=card_name,
        gemrate_id=gemrate_id,
        source="gemrate",
        timestamp=datetime.now(),
        total_population=data.get("total_population", 0),
        psa_10=psa_10,
        psa_9=psa_9,
        psa_8=psa_8,
        bgs_10=bgs_10,
        bgs_9_5=bgs_9_5,
        cgc_10=cgc_10,
        cgc_9_5=cgc_9_5,
        gem_rate=psa_gem_rate,
    )


def fetch_population(card_name: str) -> Optional[PopulationReport]:
    """Search GemRate for a card and fetch its population report.

    Args:
        card_name: Search query (e.g. "Umbreon ex 161 Prismatic")

    Returns:
        PopulationReport with grading data, or None if not found.
    """
    session, token = _get_session_and_token()

    # Search
    search_resp = session.post(
        f"{_BASE}/universal-search-query",
        json={"query": card_name},
    )
    search_resp.raise_for_status()
    results = search_resp.json()

    if not results:
        return None

    # Use first result
    best = results[0]
    gemrate_id = best["gemrate_id"]
    description = best.get("description", card_name)

    # Fetch card details
    details_resp = session.get(
        f"{_BASE}/card-details",
        params={"gemrate_id": gemrate_id},
        headers={
            "X-Card-Details-Token": token,
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    details_resp.raise_for_status()

    return parse_population(
        details_resp.json(),
        card_name=description,
        gemrate_id=gemrate_id,
    )
