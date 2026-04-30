# Fix codebase quality issues

## Problems addressed

1. **God module** — `db_queries.py` mixed DB I/O, computation, chart math, and markup generation
2. **Redundant DB loads** — dashboard triggered ~18 DB round-trips loading identical data
3. **O(n²) algorithms** — `_rank_history` and `races_led` recomputed running totals from scratch each race
4. **Private API leakage** — `_slugify`, `_load_season` imported by external modules
5. **Duplicated logic** — HTTP+caching in both `importers/pcs.py` and `scripts/import_athletes.py`
6. **Dead code** — `importers/csv_file.py` (deprecated 2026)
7. **Inline imports** — `import uuid`, `from scoring import score_result`, etc. inside function bodies
8. **`sys.path` hack** in `routers/admin.py` (unnecessary in web app context)
9. **`_streak` semantics** — checked `> 0` instead of directional trend
10. **Label collision** — `race_short` could produce identical labels for different races

## Steps

1. Create `utils.py` — public utilities extracted from `db_queries.py`:
   - `slugify`, `flag_emoji`, `fmt_date`, `race_short`, `get_race_labels` (with dedup)
   - `athlete_photo_url`, `AVATAR_COLORS`, `MONTHS_IT`
   - `NATIONALITY_TO_FLAG_EMOJI`, `FLAG_CODE_TO_COUNTRY` (shared data)

2. Rewrite `db_queries.py`:
   - Add `SeasonContext` dataclass + `load_season_context()`
   - All public functions accept optional `ctx: SeasonContext | None = None`
   - Fix `_rank_history` from O(n² × users) to O(n × users) via incremental running totals
   - Replace O(n²) `races_led` loop with `sum(1 for r in rank_hist if r == 1)`
   - Fix `_streak` to compare last vs prev points (directional trend)
   - Remove `_user_total_up_to` (unused after fix), `get_race_labels` (unused public fn)
   - Move `import uuid` to module top

3. Add `fetch_teams` + `fetch_roster` methods to `PCSImporter` — eliminates duplication

4. Rewrite `scripts/import_athletes.py` — use `PCSImporter` methods, remove duplicated `_get`, `_FLAG_TO_COUNTRY`, `fetch_teams`, `fetch_roster`

5. Rewrite `routers/dashboard.py`:
   - Call `load_season_context()` once per request
   - Pass ctx to all `db_queries.*` calls (eliminates ~18 DB round-trips → 4)
   - Move `import uuid` to top
   - Remove `db_queries._load_season()` call (was accessing private fn)

6. Fix `routers/admin.py`:
   - Remove `sys.path.insert`
   - Change `from db_queries import _slugify` → `from utils import slugify`
   - Move inline imports (`urlparse`, `PCSImporter`, `score_result`) to top

7. Fix `scripts/sync_races.py` — remove `--source csv` option

8. Delete `importers/csv_file.py` — dead code
