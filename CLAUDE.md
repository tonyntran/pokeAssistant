# pokeAssistant

A tool for Pokemon TCG collectors and researchers to track card prices and price trends using TCGPlayer data.

## Project Overview

- **Goal**: Help collectors and researchers monitor Pokemon TCG card prices and price changes
- **Data Source**: TCGPlayer pricing data
- **Tech Stack**: TBD

## Quick Commands

```bash
# TBD - fill in as stack is chosen
```

## Golden Rules

1. Never commit API keys, tokens, or secrets — use environment variables
2. Write tests before implementation
3. All price data must include timestamps and source attribution
4. Keep CLAUDE.md lean — put detailed docs in `.claude/docs/`

## Code Standards

- Use meaningful variable names that reflect the Pokemon TCG domain
- Prefer explicit over implicit — no magic numbers for price thresholds
- All monetary values stored as integers (cents) to avoid floating point issues

## Documentation

Detailed docs live in `.claude/docs/`:
- `architecture/` — System design and data flow
- `data/` — TCGPlayer API integration, data models
- `testing/` — Test patterns and coverage expectations
