# Phase: Seed Data, Race Sync & Admin Scaffolding

**Date:** 2026-04-27
**Status:** In Progress

---

## Goals

1. Fetch the latest 10 real bike races and persist results
2. Seed the database with demo users and popular cyclists
3. Give admins a UI to manually scaffold or correct races, cyclists, and results

---

## Schema (done — migration 20260427000002_pcs_ids.sql)

- `athletes.firstcycling_id` — now nullable (was NOT NULL)
- `races.firstcycling_race_id` — now nullable (was NOT NULL)
- `athletes.pcs_slug text unique` — added
- `races.pcs_slug text unique` — added

`pcs_slug` is the primary identifier for both athletes and races going forward.
`firstcycling_id` / `firstcycling_race_id` remain for future cross-referencing but are not required.

---

## Data source: PCS only

**procyclingstats.com** is the sole data source. The `first_cycling_api` wrapper requires
`slumber` (not installed) and firstcycling.com blocks plain requests — dropped entirely for now.

| What | URL pattern | Verified |
|---|---|---|
| Race calendar (2026 WT) | `races.php?year=2026&circuit=1&filter=Filter` | ✅ returns HTML table |
| Race results (one-day) | `race/{slug}/{year}/result` | ✅ positions + rider slugs |
| Race GC (stage race) | `race/{slug}/{year}/gc` | ✅ same structure |
| Rider profile | `rider/{slug}` | ✅ name, nationality, team in div.rdr-info-cont |

Parsing: `requests` + `beautifulsoup4` (already in deps). No JS rendering needed.

---

## Task 1 — Seed File

**File:** `scripts/seed.py`

Standalone script: `python scripts/seed.py`. Idempotent (upsert on conflict).

### Users to seed
- 8 regular demo users (username + bcrypt-hashed password)
- 1 admin user (`is_admin = true`)

### Cyclists to seed
Seed ~20 well-known riders by `pcs_slug`. For each slug, fetch
`procyclingstats.com/rider/{slug}` to get `full_name`, `nationality`, `team`.
Leave `firstcycling_id` null.

Known slugs (verified from race results):
- `tadej-pogacar`, `jonas-vingegaard`, `remco-evenepoel`, `primoz-roglic`
- `mathieu-van-der-poel`, `wout-van-aert`, `jasper-philipsen`, `mads-pedersen`
- `julian-alaphilippe`, `tom-pidcock`, `adam-yates`, `enric-mas`
- `filippo-ganna`, `egan-bernal`, `paul-seixas`, `isaac-del-toro`
- `tobias-lund-andresen`, `jay-vine`, `dylan-groenewegen`, `pello-bilbao`

Upsert into `athletes` on `pcs_slug`.

### Season
Ensure a `seasons` row for the current year with `active = true`.

### User–athlete assignments
Assign a random subset of cyclists to each demo user via `user_athletes`.

---

## Task 2 — Race Sync Script

**File:** `scripts/sync_races.py`

Also exposed as `GET /sync-races` (logged-in users). Records `synced_at` on each race row
so users can see when data was last refreshed.

### Steps
1. Fetch `races.php?year=2026&circuit=1&filter=Filter` — parse table for completed races
   (rows that have a winner listed). Take latest 10.
2. Determine `race_type`: if the PCS link contains `/gc` → `stage_race`; `/result` → `one_day`.
3. For each race, upsert into `races` on `pcs_slug` (set `name`, `year`, `race_type`,
   `race_date`, `synced_at = now()`).
4. Fetch the result page:
   - For one-day: `race/{slug}/{year}/result` — top-10 positions, rider slugs
   - For stage races: `race/{slug}/{year}/gc` — GC top-10; optionally stage winners
5. For each rider in results:
   - If `pcs_slug` exists in `athletes` → use that row
   - Otherwise → fetch `rider/{slug}` for name/nationality/team, insert new athlete row
6. Upsert into `race_results` on `(race_id, athlete_id, result_type, stage_number)`.

### synced_at visibility
- Admin race list shows `synced_at` per race
- Dashboard shows a global "last synced" (max `synced_at` across all races)
- Users see a "Sync now" link if data is older than 1 hour

---

## Task 3 — Admin Scaffolding UI

Extend `/admin` with full CRUD-like management pages.

### 3a — Race management (`/admin/races`)
- List all races: name, date, type, `synced_at` (formatted as relative time)
- Status badge: synced / partial (has race but no results) / manual (no `pcs_slug`)
- "Add race manually" form: name, year, race_type, race_date, num_stages
- "Edit race" form: same fields + re-sync button (calls sync logic for that race)
- Delete race (with confirmation)

### 3b — Cyclist management (`/admin/athletes`)
- List athletes with search/filter; show `pcs_slug` column
- "Add cyclist" form: full_name, pcs_slug, nationality, team
- "Edit cyclist" inline or separate page
- Delete cyclist

### 3c — Result entry (`/admin/races/{race_id}/results`)
- Table showing current results for a race
- Per-row: position, athlete (dropdown or search), result_type, stage_number, points
- "Add result" row at bottom
- "Save" button (batch upsert)
- "Auto-calculate points" button — applies scoring table from `config.py`

### 3d — Shared admin layout
- Extend `admin/index.html` with a nav sidebar: Races, Athletes, Results
- Flash messages for success/error feedback

---

## File/Route Summary

| File | Purpose |
|---|---|
| `scripts/seed.py` | Demo users + cyclists (via PCS) + season |
| `scripts/sync_races.py` | Sync latest 10 WT races from PCS |
| `routers/admin.py` | Extend with new route handlers |
| `templates/admin/races.html` | Race list + add/edit forms |
| `templates/admin/athletes.html` | Cyclist list + add/edit forms |
| `templates/admin/race_results.html` | Result entry table for a race |

---

## Order of Execution

1. **Task 1** (seed) — no dependencies, run first to populate test data
2. **Task 2** (sync) — can run independently; will auto-insert athletes it finds
3. **Task 3** (admin UI) — depends on DB shape (done); build after tasks 1 & 2 work

---

## Decisions

| Question | Decision |
|---|---|
| Primary data source | PCS only — FC wrapper dropped (missing dep, blocked requests) |
| Primary identifier | `pcs_slug` for both athletes and races |
| FC ids | Kept as nullable columns for future use, not populated by scripts |
| Race sync trigger | `GET /sync-races` (logged-in) + `python scripts/sync_races.py` CLI |
| Unknown athletes in result entry | Add in `/admin/athletes` first, then return to result entry |
| Last synced visibility | `synced_at` shown per race in admin; global max shown on dashboard |
