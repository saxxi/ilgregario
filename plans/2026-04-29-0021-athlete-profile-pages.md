# 0021 – Athlete profile pages

## Goal
Give each athlete their own internal page at `/athletes/{athlete_id}` that shows:
- Bio card (name, team, nationality, flag)
- Which user owns this athlete in the active season
- Season stats: total points, best result, per-race breakdown

Athlete names across the app (user roster cards, top athletes panel) will link to this internal page instead of (or in addition to) procyclingstats.

## Changes

### `db_queries.py`
1. Add `"id": aid` to the athletes dict in `_build_internal` so downstream callers can access the UUID.
2. Add `"id": aid` to items in `get_user_detail` → `ath_list`.
3. Add `"id": aid` to items in `get_top_athletes` → result.
4. New function `get_athlete_detail(athlete_id: str) -> dict | None` that:
   - Fetches athlete row from `athletes` table
   - Finds the owner username via `user_athletes` for the active season
   - Loads all race results for this athlete
   - Returns stats: total_points, best_result, per_race_results, owner

### `routers/dashboard.py`
- Add `GET /athletes/{athlete_id}` → `athlete_detail` handler

### `templates/dashboard/athlete.html` (new)
- Hero card: name, flag, team, nationality
- Owner chip linked to `/users/{username}`
- Stats strip: total points, best result, races scored
- Per-race results table

### Existing template updates
- `templates/dashboard/user.html`: athlete name links → `/athletes/{ath.id}` (PCS link becomes secondary)
- `templates/dashboard/index.html` top athletes panel: same change
