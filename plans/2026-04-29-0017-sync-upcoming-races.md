# 2026-04-29-0017 — Sync upcoming races

## Problem
`fetch_calendar` skips rows with no winner, so only completed races land in the DB.
`races_total == races_done` → narrative shows "0 gare alla fine".

## Solution

### 1. `importers/base.py`
Add `completed_only: bool = True` to the abstract `fetch_calendar` signature.

### 2. `importers/pcs.py`
Extend `fetch_calendar(completed_only=True)`:
- Collect completed races (has winner) → reverse → take `max_races`
- When `completed_only=False`, also collect upcoming races (no winner) in chronological order and append them after completed

### 3. `scripts/sync_races.py`
- Call `fetch_calendar(completed_only=False)` to get all races
- Upsert race metadata for every race
- Fetch + upsert results only for completed races (winner_slug is not empty)
- Upcoming races count as synced (metadata only), not skipped

## No DB schema changes needed
The `races` table already has `race_date`, `pcs_slug`, `season_id` — upcoming races fit as-is with no results.
