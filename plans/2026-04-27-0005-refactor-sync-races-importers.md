# Refactor sync_races.py — Importer Adapter Pattern

## Goal

Split the monolithic `scripts/sync_races.py` into layered, reusable modules so
that adding a second data source (e.g. FirstCycling, a JSON feed) requires only
a new file under `importers/`.

---

## Target layout

```
importers/
    __init__.py        # re-exports BaseImporter, domain models
    base.py            # Protocol + dataclasses: RaceMeta, RiderResult, RiderProfile
    pcs.py             # PCSImporter — HTTP + BS4 scraping of procyclingstats.com

scoring.py             # _gc_points / _stage_points (pure functions, no I/O)

scripts/
    sync_races.py      # sync() orchestrator + CLI entry-point
```

### Layer responsibilities

| Layer | Owns | Does NOT own |
|---|---|---|
| `importers/base.py` | domain dataclasses, `BaseImporter` ABC | any HTTP, DB, or scoring |
| `importers/pcs.py` | PCS HTTP calls, HTML parsing | DB writes, scoring |
| `scoring.py` | point lookup tables | I/O of any kind |
| `scripts/sync_races.py` | DB upserts, orchestration loop, CLI | parsing, scoring internals |

---

## Interface (`BaseImporter`)

```python
class BaseImporter(ABC):
    def fetch_calendar(self, year: int, max_races: int) -> list[RaceMeta]: ...
    def fetch_num_stages(self, race: RaceMeta) -> int | None: ...
    def fetch_results(self, race: RaceMeta) -> list[RiderResult]: ...
    def fetch_rider(self, slug: str) -> RiderProfile: ...
```

---

## Domain models (`importers/base.py`)

```python
@dataclass
class RaceMeta:
    name: str
    pcs_slug: str
    race_type: Literal["one_day", "stage_race"]
    result_path: str
    race_date: date | None
    winner_slug: str

@dataclass
class RiderResult:
    position: int
    rider_slug: str

@dataclass
class RiderProfile:
    slug: str
    full_name: str
    nationality: str
    team: str
```

---

## What moves where

| Current function | Destination |
|---|---|
| `_get()` | `importers/pcs.py` (PCSImporter._get) |
| `_parse_race_date()` | `importers/pcs.py` |
| `_parse_calendar()` | `importers/pcs.py` (fetch_calendar) |
| `_get_num_stages()` | `importers/pcs.py` (fetch_num_stages) |
| `_parse_result_rows()` | `importers/pcs.py` (fetch_results) |
| `_fetch_rider_profile()` | `importers/pcs.py` (fetch_rider) |
| `_gc_points()` | `scoring.py` |
| `_stage_points()` | `scoring.py` |
| `_upsert_athlete()` | `scripts/sync_races.py` |
| `_upsert_race()` | `scripts/sync_races.py` |
| `_upsert_result()` | `scripts/sync_races.py` |
| `sync()` | `scripts/sync_races.py` |

---

## Backwards compatibility

- `scripts/sync_races.py` keeps the same public `sync(db=None) -> dict` signature
  so `routers/admin.py` needs no changes.
- `scoring.py` is a new module; `config.py` keeps `GC_SCORING` / `STAGE_SCORING`.

---

## Steps

1. Create `importers/__init__.py`, `importers/base.py`, `importers/pcs.py`
2. Create `scoring.py`
3. Rewrite `scripts/sync_races.py` as thin orchestrator
4. Verify `routers/admin.py` import still works
