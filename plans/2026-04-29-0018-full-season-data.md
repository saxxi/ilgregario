# 0018 — Full 2026 Season Data

## Goal

Expand `tmp/pcs_reference.json` to cover the complete 2026 WorldTour season so that the JSON
importer can seed the database with realistic data at any point during the year.

## Changes

### `tmp/pcs_reference.json`

1. **`results_by_slug`** (new key) — top-10 results for every completed race, keyed by pcs_slug
   - Avoids the brittle `sample_results` + `_RESULTS_KEY_TO_SLUG` mapping in the importer
   - Easy to extend: just add another `"pcs-slug": [...]` entry
2. **`calendar_2026_wt`** — add remaining WT races (May–Oct) as upcoming entries (no `winner_slug`)
3. **`rider_profiles`** — expand to cover all riders referenced in results

### `importers/json_file.py`

- Load `results_by_slug` directly (no mapping needed)
- Keep `sample_results` + `_RESULTS_KEY_TO_SLUG` as a legacy fallback so old data still works
- Priority: `results_by_slug` > `sample_results`

## Completed races (with full results)

Jan–Apr 2026 (19 races total, winner already in calendar)

## Upcoming races added

| Race | Date | Type |
|---|---|---|
| Eschborn-Frankfurt | 01.05 | one_day |
| Giro d'Italia | 09.05–01.06 | stage_race |
| Critérium du Dauphiné | 07.06–14.06 | stage_race |
| Tour de Suisse | 13.06–21.06 | stage_race |
| Tour de France | 04.07–26.07 | stage_race |
| Clasica San Sebastian | 01.08 | one_day |
| Vuelta a España | 15.08–06.09 | stage_race |
| GP de Québec | 10.09 | one_day |
| GP de Montréal | 13.09 | one_day |
| Il Lombardia | 11.10 | one_day |
