# pokeAssistant

A tool for Pokemon TCG collectors and researchers to track card prices and price trends using TCGPlayer data.

## Features

- **TCGCSV fetcher** — free daily TCGPlayer price snapshots (no browser needed)
- **TCGPlayer scraper** — Playwright-based headless browser that intercepts XHR API calls for market prices, listing counts, and sales history
- **Google Trends** — demand signal tracking via pytrends
- **SQLite storage** — local database with deduplication, all prices stored in cents

## Requirements

- Python 3.11+
- Chromium (installed automatically via Playwright)

## Setup

```bash
# Clone and install
git clone https://github.com/tonyntran/pokeAssistant.git
cd pokeAssistant
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium

# Copy env config
cp .env.example .env
```

## Usage

```bash
# Fetch prices from TCGCSV (no browser, fastest)
pokeassistant --product-id 593355 --group-id 23821 --tcgcsv

# Scrape TCGPlayer via headless browser
pokeassistant --product-id 593355 --scrape

# Fetch Google Trends data
pokeassistant --product-id 593355 --trends --keyword "prismatic evolutions"

# Run all sources
pokeassistant --product-id 593355 --group-id 23821 --all

# Run browser in visible mode (debugging)
pokeassistant --product-id 593355 --scrape --no-headless
```

### Finding IDs

- **Product ID**: The number in any TCGPlayer product URL (e.g. `tcgplayer.com/product/593355`)
- **Group ID**: Use the TCGCSV groups endpoint — Prismatic Evolutions is `23821`

## Data Sources

| Source | What it provides | Browser needed |
|--------|-----------------|----------------|
| TCGCSV | Daily low/market/high prices | No |
| TCGPlayer scrape | Market prices, listing count, sales history | Yes |
| Google Trends | Search interest over time (0-100) | No |

## Database

SQLite database stored at `data/pokeassistant.db` with 4 tables:

- **products** — product metadata
- **price_snapshots** — timestamped price data (cents) with source attribution
- **sale_records** — daily sales volume from TCGPlayer history
- **trend_data** — Google Trends interest scores

All monetary values are stored as **integers (cents)** to avoid floating point issues.

## Development

```bash
# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/
```

## Project Structure

```
src/pokeassistant/
├── cli.py              # CLI entry point (argparse)
├── config.py           # Env var loading, defaults
├── db.py               # SQLite schema + insert/query helpers
├── models.py           # Dataclasses: Product, PriceSnapshot, SaleRecord, TrendDataPoint
└── scrapers/
    ├── tcgcsv.py       # Free daily price snapshots (no browser)
    ├── tcgplayer.py    # Playwright scraper with XHR interception
    └── trends.py       # Google Trends via pytrends
```
