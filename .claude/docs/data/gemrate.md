# GemRate Integration

## Overview

GemRate (https://www.gemrate.com/) is a grading analytics platform that tracks PSA (and other grader) pop reports, gem rates, and grading trends for collectible trading cards. It serves as a data source for grading population data and gem rate statistics — key inputs for price prediction and value assessment.

## Why GemRate Matters

- **Gem rate** (% of submissions that receive a PSA 10) directly impacts card value — low gem rates mean PSA 10 copies are scarcer and command higher premiums
- **Pop counts** (total graded population) indicate supply of graded copies at each grade level
- **Grading trends** (submission volume over time) can signal increased demand or speculation on a card

## Data Points Available

- Card name, card number, variant (Base, Reverse Holo, etc.)
- Total grades (all-time PSA submissions)
- Grade breakdown (G1 through G10 counts)
- Gem rate (PSA 10 percentage)
- 30-day growth metrics
- 52-week grading trend arrays (weekly submission volume)
- Links to CardLadder sales history

## URL Structure

Pop reports are accessible via query parameters:

```
https://www.gemrate.com/item-details-advanced?grader=PSA&category=tcg-cards&year={YEAR}&set_name={SET_NAME}
```

Example for Surging Sparks:
```
https://www.gemrate.com/item-details-advanced?grader=PSA&category=tcg-cards&year=2024&set_name=Pokemon+Ssp+EN-Surging+Sparks
```

### Known Parameters

| Parameter  | Description                          | Example Value                          |
|------------|--------------------------------------|----------------------------------------|
| `grader`   | Grading company                      | `PSA`                                  |
| `category` | Card category                        | `tcg-cards`                            |
| `year`     | Release year                         | `2024`                                 |
| `set_name` | Set identifier (URL-encoded spaces)  | `Pokemon+Ssp+EN-Surging+Sparks`        |

## Data Access Method

- Data is embedded as inline JSON in a `RowData` JavaScript variable in the page HTML
- **No headless browser required** — a standard HTTP GET returns the full dataset
- Parse the `RowData` JSON from the HTML response to extract card-level data
- Each set page contains the full card list for that set/grader combination

## Integration Notes

- TBD: Map GemRate set names to TCGPlayer set names (naming conventions differ)
- TBD: Determine full list of available Pokemon TCG sets and their `set_name` values
- TBD: Define data refresh intervals (gem rates change as new submissions are graded)
- TBD: Rate limiting — unknown; be respectful with request frequency
- TBD: Explore if other graders (BGS, CGC) have the same URL pattern
