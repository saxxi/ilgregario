# 2026-04-29-0020 — Import All Athletes from PCS Team Rosters

## Problem
Only 114 athletes in DB — just race winners captured during sync.
For fantasy play users need to be able to pick from the full professional peloton.

## Goal
Script that bulk-imports all riders from WorldTour (and optionally ProTeams)
team rosters via PCS scraping. Target: ~530 WorldTour riders.

## Changes

### `scripts/import_athletes.py` (new)
- Fetch team list from `procyclingstats.com/teams.php?year=2026&filter=Filter`
- Filter to desired circuit (default: WorldTour, `--circuit ProTeams` to add more)
- For each team, fetch `procyclingstats.com/team/{slug}/2026` roster page
- Parse rider rows: slug, full name, nationality
- Upsert into `athletes` table (on_conflict=`pcs_slug`)
- Polite delay (0.5s) between requests, HTML cache in `tmp/pcs_html/`

## CLI
```
python scripts/import_athletes.py                      # WorldTour only
python scripts/import_athletes.py --circuit ProTeams   # add ProTeams tier
python scripts/import_athletes.py --no-cache           # skip cache
```

## No DB schema changes needed
