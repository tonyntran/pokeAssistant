"""FastAPI application with all endpoints."""

from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from pokeassistant.database import get_db, get_session_factory
from pokeassistant.repositories.sqlalchemy_repo import SQLAlchemyRepository
from pokeassistant.schemas import (
    HealthResponse, PaginatedResponse, CardSummary, CardDetail,
    ProductSummary, ProductDetail, PriceHistoryPoint,
    GradingRow, PopulationRow, TrendPoint, SearchResult, ConditionPrice,
)

app = FastAPI(title="PokeAssistant API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

VALID_CARD_SORTS = {"market_price", "name", "change"}
VALID_PRODUCT_SORTS = {"market_price", "name", "change", "release_date"}


def get_repo(session: Session = Depends(get_db)) -> SQLAlchemyRepository:
    return SQLAlchemyRepository(session)


# --- Health ---

@app.get("/api/health", response_model=HealthResponse)
def health_check(session: Session = Depends(get_db)):
    try:
        session.execute(text("SELECT 1"))
        return HealthResponse(status="ok", db="connected")
    except Exception:
        return HealthResponse(status="degraded", db="disconnected")


# --- Cards ---

@app.get("/api/cards", response_model=PaginatedResponse[CardSummary])
def list_cards(
    repo: SQLAlchemyRepository = Depends(get_repo),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    category: str | None = None,
    search: str | None = None,
    sort_by: str = "market_price",
    order: str = "desc",
):
    if sort_by not in VALID_CARD_SORTS:
        raise HTTPException(422, f"Invalid sort_by. Valid: {VALID_CARD_SORTS}")
    if order not in ("asc", "desc"):
        raise HTTPException(422, "Invalid order. Valid: asc, desc")

    cards, total = repo.list_cards(
        limit=limit, offset=offset, category=category,
        search=search, sort_by=sort_by, order=order,
    )

    items = []
    for card in cards:
        change_cents, change_pct = repo.get_price_change(card.product_id)
        latest_snap = (card.price_snapshots[-1] if card.price_snapshots else None)
        market = latest_snap.market_price_cents if latest_snap else None

        # PSA 10 from latest graded price
        latest_gp = (card.graded_prices[-1] if card.graded_prices else None)
        psa10 = latest_gp.psa_10_cents if latest_gp else None
        psa10_pct = None
        if psa10 and market and market > 0:
            psa10_pct = round((psa10 - market) / market * 100, 1)

        items.append(CardSummary(
            id=card.product_id,
            name=card.name,
            set=card.group_name,
            num=card.card_number,
            image_url=card.image_url,
            market_price_cents=market,
            psa10_price_cents=psa10,
            psa10_premium_pct=psa10_pct,
            change_cents=change_cents,
            change_pct=change_pct,
        ))

    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@app.get("/api/cards/{product_id}", response_model=CardDetail)
def get_card(product_id: int, repo: SQLAlchemyRepository = Depends(get_repo)):
    card = repo.get_card(product_id)
    if not card:
        raise HTTPException(404, "Card not found")

    change_cents, change_pct = repo.get_price_change(product_id)
    latest_snap = card.price_snapshots[-1] if card.price_snapshots else None
    market = latest_snap.market_price_cents if latest_snap else None
    listing_count = latest_snap.listing_count if latest_snap else None

    latest_gp = card.graded_prices[-1] if card.graded_prices else None
    psa10 = latest_gp.psa_10_cents if latest_gp else None
    psa10_pct = None
    if psa10 and market and market > 0:
        psa10_pct = round((psa10 - market) / market * 100, 1)

    # Condition prices (industry standard multipliers)
    condition_prices = []
    if market:
        for cond, mult in [("NM", 1.0), ("LP", 0.76), ("MP", 0.60), ("HP", 0.40)]:
            condition_prices.append(ConditionPrice(
                condition=cond, price_cents=round(market * mult),
            ))

    return CardDetail(
        id=card.product_id,
        name=card.name,
        set=card.group_name,
        num=card.card_number,
        image_url=card.image_url,
        market_price_cents=market,
        psa10_price_cents=psa10,
        psa10_premium_pct=psa10_pct,
        change_cents=change_cents,
        change_pct=change_pct,
        category=card.category,
        rarity=card.rarity,
        url=card.url,
        condition_prices=condition_prices,
        listing_count=listing_count,
    )


@app.get("/api/cards/{product_id}/price-history", response_model=list[PriceHistoryPoint])
def card_price_history(
    product_id: int,
    repo: SQLAlchemyRepository = Depends(get_repo),
    period: str = "1M",
):
    snapshots = repo.get_price_history(product_id, period=period)
    return [
        PriceHistoryPoint(
            timestamp=s.timestamp,
            market_price_cents=s.market_price_cents,
            low_price_cents=s.low_price_cents,
            high_price_cents=s.high_price_cents,
        )
        for s in snapshots
    ]


# --- Products ---

@app.get("/api/products", response_model=PaginatedResponse[ProductSummary])
def list_products(
    repo: SQLAlchemyRepository = Depends(get_repo),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str | None = None,
    sort_by: str = "market_price",
    order: str = "desc",
):
    if sort_by not in VALID_PRODUCT_SORTS:
        raise HTTPException(422, f"Invalid sort_by. Valid: {VALID_PRODUCT_SORTS}")
    if order not in ("asc", "desc"):
        raise HTTPException(422, "Invalid order. Valid: asc, desc")

    products, total = repo.list_products(
        limit=limit, offset=offset, search=search,
        sort_by=sort_by, order=order,
    )

    items = []
    for prod in products:
        change_cents, change_pct = repo.get_price_change(prod.product_id)
        latest_snap = prod.price_snapshots[-1] if prod.price_snapshots else None
        market = latest_snap.market_price_cents if latest_snap else None

        items.append(ProductSummary(
            id=prod.product_id,
            name=prod.name,
            set=prod.group_name,
            image_url=prod.image_url,
            market_price_cents=market,
            change_cents=change_cents,
            change_pct=change_pct,
            release_date=prod.release_date,
        ))

    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)


@app.get("/api/products/{product_id}", response_model=ProductDetail)
def get_product(product_id: int, repo: SQLAlchemyRepository = Depends(get_repo)):
    prod = repo.get_product(product_id)
    if not prod:
        raise HTTPException(404, "Product not found")

    change_cents, change_pct = repo.get_price_change(product_id)
    latest_snap = prod.price_snapshots[-1] if prod.price_snapshots else None
    market = latest_snap.market_price_cents if latest_snap else None

    return ProductDetail(
        id=prod.product_id,
        name=prod.name,
        set=prod.group_name,
        image_url=prod.image_url,
        market_price_cents=market,
        change_cents=change_cents,
        change_pct=change_pct,
        release_date=prod.release_date,
        category=prod.category,
        url=prod.url,
    )


@app.get("/api/products/{product_id}/price-history", response_model=list[PriceHistoryPoint])
def product_price_history(
    product_id: int,
    repo: SQLAlchemyRepository = Depends(get_repo),
    period: str = "1M",
):
    snapshots = repo.get_price_history(product_id, period=period)
    return [
        PriceHistoryPoint(
            timestamp=s.timestamp,
            market_price_cents=s.market_price_cents,
            low_price_cents=s.low_price_cents,
            high_price_cents=s.high_price_cents,
        )
        for s in snapshots
    ]


# --- Search ---

@app.get("/api/search", response_model=list[SearchResult])
def search_products(
    q: str = "",
    type: str | None = None,
    repo: SQLAlchemyRepository = Depends(get_repo),
):
    if not q:
        return []
    results = repo.search(q, result_type=type)
    return [
        SearchResult(
            type="card" if r.product_type == "card" else "product",
            name=r.name,
            sub=r.group_name,
            price_cents=(r.price_snapshots[-1].market_price_cents
                        if r.price_snapshots else None),
            image_url=r.image_url,
        )
        for r in results
    ]


# --- Trends ---

@app.get("/api/trends/{keyword}", response_model=list[TrendPoint])
def get_trends(keyword: str, repo: SQLAlchemyRepository = Depends(get_repo)):
    points = repo.get_trend_data(keyword)
    return [
        TrendPoint(date=p.date, interest=p.interest, keyword=p.keyword)
        for p in points
    ]


# --- Grading ---

@app.get("/api/grading/{product_id}", response_model=list[GradingRow])
def get_grading(product_id: int, repo: SQLAlchemyRepository = Depends(get_repo)):
    graded = repo.get_grading(product_id)
    if not graded:
        return []

    latest = graded[0]  # Ordered by timestamp desc
    rows = []
    grade_map = [
        ("PSA 10", latest.psa_10_cents),
        ("Grade 9.5", latest.grade_9_5_cents),
        ("Grade 9", latest.grade_9_cents),
        ("Grade 8", latest.grade_8_cents),
        ("Grade 7", latest.grade_7_cents),
        ("Ungraded", latest.ungraded_cents),
    ]
    for grade, price in grade_map:
        if price is not None:
            rows.append(GradingRow(grade=grade, price_cents=price))

    return rows


# --- Population ---

@app.get("/api/population/{product_id}", response_model=list[PopulationRow])
def get_population(product_id: int, repo: SQLAlchemyRepository = Depends(get_repo)):
    reports = repo.get_population(product_id)
    if not reports:
        return []

    latest = reports[0]  # Ordered by timestamp desc
    rows = []
    pop_map = [
        ("PSA 10", latest.psa_10),
        ("PSA 9", latest.psa_9),
        ("PSA 8", latest.psa_8),
        ("BGS 10", latest.bgs_10),
        ("BGS 9.5", latest.bgs_9_5),
        ("CGC 10", latest.cgc_10),
        ("CGC 9.5", latest.cgc_9_5),
    ]
    for grade, count in pop_map:
        if count is not None:
            rows.append(PopulationRow(grade=grade, count=count))

    return rows


# --- Server Entry ---

def run_server():
    """Entry point for `pokeassistant-api` script."""
    import uvicorn
    uvicorn.run("pokeassistant.api:app", host="0.0.0.0", port=8000, reload=True)
