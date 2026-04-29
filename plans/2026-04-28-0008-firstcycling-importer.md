# FirstCycling Importer — Per-object Sync

## Goal

Replace the PCS batch sync with a FirstCycling-backed system that supports
syncing individual athletes, races, and teams on demand from the admin panel.

---

## Why FirstCycling

| | ProcyclingStats | FirstCycling |
|---|---|---|
| Identifier | text slug (changes on rename/transfer) | stable numeric ID |
| DB support | `pcs_slug` columns added via migration | `firstcycling_id` / `firstcycling_race_id` already in schema |
| Granular sync | not supported today | numeric ID maps directly to a single HTTP fetch |

The DB schema was always designed for FC ids; PCS slugs were a workaround.
This plan returns to that intent.

---

## URL patterns on firstcycling.com

| Resource | URL |
|---|---|
| Rider profile | `/rider/{fc_id}` |
| Race overview | `/race/{fc_race_id}` |
| Race results (year) | `/race/{fc_race_id}/result?l={year}` |
| Team roster | `/team/{fc_team_id}/{year}` |
| WT calendar | `/calendar.php?CN=1&y={year}` (or equivalent filter) |

These must be verified by loading the pages before implementing the scraper;
structure may have changed.

---

## Target layout

```
importers/
    base.py          # add fc_id fields to RaceMeta, RiderProfile; add TeamRoster
    fc.py            # NEW — FCImporter
    pcs.py           # keep untouched; remove from sync orchestrator
    json_file.py     # keep for offline testing

scripts/
    sync_races.py    # update default importer to FCImporter

supabase/migrations/
    20260428000005_fc_indexes.sql   # indexes on firstcycling_id columns
```

---

## Domain model changes (`importers/base.py`)

Extend existing dataclasses with optional FC id fields — additive, no breakage:

```python
@dataclass
class RaceMeta:
    ...
    fc_id: int | None = None        # firstcycling race id

@dataclass
class RiderProfile:
    ...
    fc_id: int | None = None        # firstcycling rider id

@dataclass
class TeamRoster:
    fc_id: int
    name: str
    year: int
    riders: list[RiderProfile]
```

---

## New module: `importers/fc.py`

`FCImporter` implements `BaseImporter` (so `sync_races.py` needs no changes)
plus three extra per-object methods:

```python
class FCImporter(BaseImporter):

    # --- BaseImporter (bulk calendar flow) ---

    def fetch_calendar(self, year: int, max_races: int) -> list[RaceMeta]:
        # scrape /calendar.php?CN=1&y={year}, extract race links → fc_id + name

    def fetch_num_stages(self, race: RaceMeta) -> int | None:
        # scrape /race/{fc_id}, count stage links

    def fetch_results(self, race: RaceMeta) -> list[RiderResult]:
        # scrape /race/{fc_id}/result?l={year}, parse result table

    def fetch_rider(self, slug: str) -> RiderProfile:
        # slug is fc_id as string; delegates to fetch_rider_by_fc_id

    # --- FC-specific (per-object sync) ---

    def fetch_rider_by_fc_id(self, fc_id: int) -> RiderProfile:
        # scrape /rider/{fc_id}; parse name, nationality, team

    def fetch_race_results_by_fc_id(
        self, fc_id: int, year: int
    ) -> tuple[RaceMeta, list[RiderResult]]:
        # scrape /race/{fc_id}/result?l={year}
        # return race metadata + ordered results

    def fetch_team(self, fc_team_id: int, year: int) -> TeamRoster:
        # scrape /team/{fc_team_id}/{year}; parse rider list
```

Shared HTTP helper: polite delay (0.5 s), retry once on 5xx,
`User-Agent: IlGregario/1.0`.

---

## DB migration (`20260428000005_fc_indexes.sql`)

```sql
-- faster per-object lookups by FC id
create index if not exists athletes_fc_id_idx
    on athletes (firstcycling_id)
    where firstcycling_id is not null;

create index if not exists races_fc_id_idx
    on races (firstcycling_race_id)
    where firstcycling_race_id is not null;
```

No structural changes — existing columns are enough for v1.
A `teams` table can be added in a later plan if needed.

---

## New admin endpoints (`routers/admin.py`)

```
POST /admin/sync/athlete/{athlete_id}
    — looks up athlete.firstcycling_id
    — calls importer.fetch_rider_by_fc_id(fc_id)
    — updates full_name, nationality, team, last_synced_at
    — redirects to /admin/athletes with flash msg

POST /admin/sync/race/{race_id}
    — looks up race.firstcycling_race_id and race.year
    — calls importer.fetch_race_results_by_fc_id(fc_id, year)
    — upserts race metadata + results (same logic as current sync())
    — redirects to /admin/races/{race_id}/results with flash msg

POST /admin/sync/calendar
    — replaces current POST /sync-races
    — calls importer.fetch_calendar(year, max_races) then syncs each race
    — returns JSON summary (same shape as today for backwards compat)
```

Admin guard (`_guard`) applied to all three.

---

## Admin UI changes

**`templates/admin/athletes.html`** — add per-row "Sync" button next to each
athlete that has a `firstcycling_id` set; posts to
`/admin/sync/athlete/{id}`.

**`templates/admin/races.html`** — add per-row "Sync" button for races that
have `firstcycling_race_id` set; posts to `/admin/sync/race/{id}`.

**`templates/admin/index.html`** — rename "Sincronizza risultati" button to
post to `/admin/sync/calendar` (same URL shape, no template logic change).

---

## `scripts/sync_races.py` changes

Change the default importer from `PCSImporter` to `FCImporter`.
Keep the `--source` CLI flag; add `--source fc` as the new default.

---

## Steps

1. Verify FC HTML structure by loading sample pages (rider, race result,
   calendar) and noting CSS classes / table structure before writing parsers.
2. Extend `importers/base.py` with `fc_id` fields and `TeamRoster`.
3. Implement `importers/fc.py` (start with `fetch_rider_by_fc_id` and
   `fetch_race_results_by_fc_id`; add `fetch_calendar` last).
4. Write `supabase/migrations/20260428000005_fc_indexes.sql`.
5. Add `/admin/sync/athlete/{id}`, `/admin/sync/race/{id}`,
   `/admin/sync/calendar` to `routers/admin.py`.
6. Update admin templates with per-row Sync buttons.
7. Switch `sync_races.py` default to `FCImporter`.
8. Smoke-test: sync one athlete and one race from the admin panel.
