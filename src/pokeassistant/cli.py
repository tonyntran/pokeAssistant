"""CLI entry point for pokeAssistant."""

import argparse
import asyncio
import sys
from datetime import datetime

from pokeassistant.config import get_db_path
from pokeassistant.database import get_engine, get_session_factory
from pokeassistant.repositories import SQLAlchemyRepository
from pokeassistant.models import Product


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pokeassistant",
        description="Pokemon TCG price tracking and analysis tool",
    )
    parser.add_argument(
        "--product-id",
        type=int,
        required=True,
        help="TCGPlayer product ID to track",
    )
    parser.add_argument(
        "--group-id",
        type=int,
        default=None,
        help="TCGPlayer group/set ID (required for --tcgcsv)",
    )
    parser.add_argument(
        "--scrape",
        action="store_true",
        help="Scrape TCGPlayer product page via Playwright",
    )
    parser.add_argument(
        "--tcgcsv",
        action="store_true",
        help="Fetch prices from TCGCSV (no browser needed)",
    )
    parser.add_argument(
        "--trends",
        action="store_true",
        help="Fetch Google Trends data",
    )
    parser.add_argument(
        "--pricecharting",
        action="store_true",
        help="Fetch graded card prices from PriceCharting",
    )
    parser.add_argument(
        "--gemrate",
        action="store_true",
        help="Fetch grading population data from GemRate",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all data sources",
    )
    parser.add_argument(
        "--card-name",
        type=str,
        default=None,
        help="Card name for PriceCharting/GemRate search (e.g. 'umbreon ex 161 prismatic evolutions')",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser in headed mode (visible)",
    )
    parser.add_argument(
        "--keyword",
        action="append",
        default=[],
        help="Google Trends keyword (can be specified multiple times)",
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    run_scrape = args.all or args.scrape
    run_tcgcsv = args.all or args.tcgcsv
    run_trends = args.all or args.trends
    run_pricecharting = args.all or args.pricecharting
    run_gemrate = args.all or args.gemrate

    if not (run_scrape or run_tcgcsv or run_trends or run_pricecharting or run_gemrate):
        print(
            "Error: Specify at least one source: --scrape, --tcgcsv, --trends, --pricecharting, --gemrate, or --all",
            file=sys.stderr,
        )
        sys.exit(1)

    if (run_pricecharting or run_gemrate) and not args.card_name:
        print(
            "Error: --card-name is required for --pricecharting and --gemrate",
            file=sys.stderr,
        )
        sys.exit(1)

    db_path = get_db_path()
    engine = get_engine()
    SessionLocal = get_session_factory(engine)
    session = SessionLocal()
    repo = SQLAlchemyRepository(session)
    print(f"Database: {db_path}")

    # --- TCGCSV ---
    if run_tcgcsv:
        print("\n--- TCGCSV ---")
        group_id = args.group_id
        if group_id is None:
            print("No --group-id provided, searching for product group...")
            from pokeassistant.scrapers.tcgcsv import fetch_groups
            groups = fetch_groups()
            # Try to find group containing this product (we'd need products endpoint)
            # For now, require --group-id for tcgcsv
            print("Error: --group-id is required for --tcgcsv")
            print("Use TCGCSV groups endpoint to find the right group ID")
        else:
            from pokeassistant.scrapers.tcgcsv import get_price_snapshot_for_product, fetch_products
            snapshot = get_price_snapshot_for_product(group_id, args.product_id)
            if snapshot:
                # Ensure product exists in DB
                products = fetch_products(group_id, as_models=True)
                for p in products:
                    if p.product_id == args.product_id:
                        repo.upsert_product(p)
                        break
                else:
                    repo.upsert_product(Product(
                        product_id=args.product_id,
                        name=f"Product {args.product_id}",
                    ))

                repo.insert_price_snapshot(snapshot)
                print(f"Price snapshot saved:")
                print(f"  Low:    ${snapshot.low_price_cents / 100:.2f}" if snapshot.low_price_cents else "  Low:    N/A")
                print(f"  Market: ${snapshot.market_price_cents / 100:.2f}" if snapshot.market_price_cents else "  Market: N/A")
                print(f"  High:   ${snapshot.high_price_cents / 100:.2f}" if snapshot.high_price_cents else "  High:   N/A")
            else:
                print(f"Product {args.product_id} not found in TCGCSV group {group_id}")

    # --- TCGPlayer Scrape ---
    if run_scrape:
        print("\n--- TCGPlayer Scrape ---")
        from pokeassistant.scrapers.tcgplayer import scrape_product
        headless = not args.no_headless
        result = asyncio.run(scrape_product(args.product_id, headless=headless))

        if result["product"]:
            repo.upsert_product(result["product"])
            print(f"Product: {result['product'].name}")
        else:
            print("Warning: Could not capture product details from TCGPlayer")
            print("  The page may have blocked the request or timed out")

        if result["snapshot"]:
            repo.insert_price_snapshot(result["snapshot"])
            snap = result["snapshot"]
            print(f"Price snapshot saved:")
            print(f"  Low:      ${snap.low_price_cents / 100:.2f}" if snap.low_price_cents else "  Low:      N/A")
            print(f"  Market:   ${snap.market_price_cents / 100:.2f}" if snap.market_price_cents else "  Market:   N/A")
            print(f"  High:     ${snap.high_price_cents / 100:.2f}" if snap.high_price_cents else "  High:     N/A")
            print(f"  Listings: {snap.listing_count}" if snap.listing_count else "  Listings: N/A")

        if result["sale_records"]:
            for rec in result["sale_records"]:
                repo.insert_sale_record(rec)
            print(f"Sale records saved: {len(result['sale_records'])} daily buckets")
        else:
            print("No sale records captured (price history XHR may not have fired)")

    # --- Google Trends ---
    if run_trends:
        print("\n--- Google Trends ---")
        from pokeassistant.scrapers.trends import fetch_trends
        keywords = args.keyword if args.keyword else ["prismatic evolutions"]
        print(f"Keywords: {keywords}")

        points = fetch_trends(keywords)
        if points:
            for td in points:
                repo.insert_trend_data(td)
            print(f"Trend data saved: {len(points)} data points")
            # Show latest
            latest = max(points, key=lambda p: p.date)
            print(f"  Latest: {latest.keyword} = {latest.interest} ({latest.date})")
        else:
            print("No trend data returned (pytrends may be rate-limited)")

    # --- PriceCharting ---
    if run_pricecharting:
        print("\n--- PriceCharting ---")
        from pokeassistant.scrapers.pricecharting import fetch_graded_prices
        gp = fetch_graded_prices(args.card_name, product_id=args.product_id)
        if gp:
            repo.insert_graded_price(gp)
            print(f"Graded prices saved for: {gp.card_name}")
            if gp.psa_10_cents:
                print(f"  PSA 10:  ${gp.psa_10_cents / 100:.2f}")
            if gp.grade_9_cents:
                print(f"  Grade 9: ${gp.grade_9_cents / 100:.2f}")
            if gp.bgs_10_cents:
                print(f"  BGS 10:  ${gp.bgs_10_cents / 100:.2f}")
            if gp.cgc_10_cents:
                print(f"  CGC 10:  ${gp.cgc_10_cents / 100:.2f}")
        else:
            print(f"Card not found on PriceCharting: {args.card_name}")

    # --- GemRate ---
    if run_gemrate:
        print("\n--- GemRate ---")
        from pokeassistant.scrapers.gemrate import fetch_population
        pr = fetch_population(args.card_name)
        if pr:
            repo.insert_population_report(pr)
            print(f"Population report saved for: {pr.card_name}")
            print(f"  Total population: {pr.total_population:,}")
            if pr.psa_10 is not None:
                print(f"  PSA 10: {pr.psa_10:,}")
            if pr.gem_rate is not None:
                print(f"  Gem rate: {pr.gem_rate:.1f}%")
        else:
            print(f"Card not found on GemRate: {args.card_name}")

    session.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
