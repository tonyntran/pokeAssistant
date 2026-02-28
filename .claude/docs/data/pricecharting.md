# PriceCharting Integration

## Overview

PriceCharting (https://www.pricecharting.com/) aggregates sales data from TCGPlayer and eBay to provide current and historical pricing for Pokemon TCG cards. It covers both ungraded and graded (PSA, BGS, CGC) cards with price history charts.

## Why PriceCharting Matters

- **Ungraded pricing** — current market value for raw cards at near-mint condition
- **Graded pricing** — prices broken down by grade level (7, 8, 9, 9.5, PSA 10), showing the premium grading adds at each tier
- **Historical price trends** — price data over time (from card release through present), essential for time series modeling and trend analysis
- **Sales volume** — approximate daily/weekly sales frequency, useful as a liquidity indicator

## Data Points Available

### Ungraded
- Current market price (near-mint)
- Historical price chart data points over time

### Graded (by grade level)
- Grade 7, 8, 9, 9.5, PSA 10 prices
- Historical price trends per grade
- Sales volume per grade (daily/weekly averages)

### General
- Card name, set, card number
- Price range and volatility over time
- Cross-platform sales data (TCGPlayer + eBay aggregated)

## URL Structure

Card pages follow a consistent pattern:

```
https://www.pricecharting.com/game/{set-name}/{card-name-number}
```

Example for Pikachu ex #238 from Surging Sparks:
```
https://www.pricecharting.com/game/pokemon-surging-sparks/pikachu-ex-238
```

### URL Conventions
- Set names are lowercase, hyphen-separated, prefixed with `pokemon-`
- Card names are lowercase, hyphen-separated
- Card number appended at the end

## Data Access Method

- Pages are server-rendered HTML — **no headless browser required**
- Price data is embedded directly in the page content
- Historical chart data may require parsing embedded JavaScript or chart data attributes
- More accessible than TCGPlayer (which requires JS rendering)

## Integration Notes

- TBD: Map PriceCharting set/card URL slugs to TCGPlayer and GemRate identifiers
- TBD: Determine how to extract historical chart data points programmatically
- TBD: Define data refresh intervals (prices update as new sales occur)
- TBD: Rate limiting — unknown; be respectful with request frequency
- TBD: Explore PriceCharting's own API (they may offer one for bulk data access)
