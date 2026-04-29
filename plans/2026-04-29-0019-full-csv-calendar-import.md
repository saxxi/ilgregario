# 2026-04-29-0019 — Full 2026 CSV Calendar Import

## Problem
`Cycling_Calendar_Expanded_2026.csv` starts at 2026-04-28 and has no PCS slugs or winner data.
Jan–Apr completed races only exist in `tmp/pcs_reference.json`.
There is no CSV-based importer in the pipeline.

## Goal
Make the CSV the authoritative calendar for 2026 (Jan 1 – Dec 31) and wire it into the sync pipeline.

## Changes

### 1. `Cycling_Calendar_Expanded_2026.csv`
- Add columns: `PCS Slug`, `Winner Slug`
- Prepend Jan–Apr completed races (from `pcs_reference.json`)
- All rows sorted chronologically

### 2. `importers/csv_file.py` (new)
- `CSVFileImporter(path)` implementing `BaseImporter`
- `fetch_calendar` → reads CSV, builds `RaceMeta` list; completed = has winner_slug
- `fetch_num_stages` → calculates from date range (`YYYY-MM-DD to YYYY-MM-DD`)
- `fetch_results` → winner-only fallback (position=1) like JSONFileImporter
- `fetch_rider` → basic profile from slug (slug-to-name conversion)

### 3. `scripts/sync_races.py`
- Add `--source csv` option (alongside existing `pcs` and `json`)
- `--path` defaults to `Cycling_Calendar_Expanded_2026.csv` when source is csv

## CSV format
```
Date,Race Name,Series,Type,PCS Slug,Winner Slug
2026-01-20 to 2026-01-25,Santos Tour Down Under,UCI WorldTour,Stage Race,tour-down-under,jay-vine
2026-01-26,Gran Camiño,UCI ProSeries,Stage Race,gran-camino,
...
```

## No DB schema changes needed
Existing `races` table already supports all fields.
