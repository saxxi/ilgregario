# Race Detail Page

## Goal
Add a `/races/{race_id}` detail page showing the full GC result for a race, with athlete positions and points, and a callout if the logged-in user has athletes in that race.

## Changes

### 1. `db_queries.py`
- Add `id` field to `get_all_races()` so each race has a linkable ID.
- Add `get_race_detail(race_id)` function returning:
  - race metadata (name, date, type, pcs_slug, year, difficulty, prestige, num_stages)
  - `results`: list of `{position, athlete_id, full_name, team, flag, pcs_slug, status, points, owned_by}` sorted by position
  - `user_athletes`: list of athlete_ids belonging to the logged-in user (passed as arg or derived from session — we'll pass `user_id` and look up)
  - A flag `is_completed`

### 2. `routers/dashboard.py`
- Add `GET /races/{race_id}` route that:
  - Calls `db_queries.get_race_detail(race_id)`
  - Passes session user_id so the query can mark owned athletes
  - Returns 404 if race not found
  - Renders `dashboard/race.html`

### 3. `templates/dashboard/races.html`
- Make each race row a link to `/races/{race.id}` when completed (or always).

### 4. `templates/dashboard/race.html` (new)
- Back link → /races
- Hero card: race name, date, type, difficulty/prestige badges
- User callout: if logged in and user has athletes in this race, show a highlighted banner with their athletes and points
- Full results table: position, athlete name (linked to /athletes/{id}), team, points
  - Highlight rows for user-owned athletes
- Empty state if no results yet
