# Split Large Files: Component Architecture for Monolith

**Date:** 2026-04-30  
**Goal:** Break up `db_queries.py` (941 lines) and `routers/admin.py` (680 lines) into focused, industry-standard modules.

---

## Files to Split

### 1. `db_queries.py` → `queries/` package

Reorganize by feature/page domain:

| New File | Contents |
|---|---|
| `queries/__init__.py` | Re-export all public functions (backwards compat) |
| `queries/context.py` | `SeasonContext` dataclass + `load_season_context()` + all `_load_*` helpers |
| `queries/dashboard.py` | `get_leaderboard`, `get_race_weekly_maxes`, `get_race_chart_data`, `get_recent_races`, `get_top_athletes`, `get_next_race`, `get_season_narrative`, `get_season_progress` + internal helpers |
| `queries/detail.py` | `get_user_detail`, `get_all_races`, `get_race_detail`, `get_athlete_detail`, `get_all_users_with_rosters` + internal helpers |

Internal helpers (`_build_internal`, `_user_race_points_list`, `_rank_history`, `_per_race_ranks`, `_streak`, `_rank_chart_data`, `_user_link`) live in the same file as the public function that uses them.

### 2. `routers/admin.py` → `routers/admin/` package

Split by resource:

| New File | Routes |
|---|---|
| `routers/admin/__init__.py` | Combine all sub-routers, export `router` |
| `routers/admin/shared.py` | `_guard()`, `_redir()`, shared imports |
| `routers/admin/users.py` | `/admin/users` — list, create, detail, edit, delete |
| `routers/admin/athletes.py` | `/admin/athletes` — list, fc-fetch, create, edit, delete, fetch-photos |
| `routers/admin/races.py` | `/admin/races` + `/admin/races/{id}/results` — races CRUD + results CRUD |
| `routers/admin/seasons.py` | `/admin/seasons` — list, create, edit, activate, delete |
| `routers/admin/overview.py` | `GET /admin` index + `POST /sync-races` |

---

## Import Changes

- `main.py` imports `routers.admin` — no change needed (re-exported from `__init__.py`)
- `routers/dashboard.py` imports `db_queries` — update to `import queries as db_queries` (or per-function imports)
- `scripts/` and other callers of `db_queries` — update accordingly

---

## Implementation Order

1. Create `queries/` package with split files
2. Update `routers/dashboard.py` imports
3. Update any other callers (`scripts/`, etc.)
4. Delete original `db_queries.py`
5. Create `routers/admin/` package with split files
6. Update `main.py` if needed
7. Delete original `routers/admin.py`

---

## Non-Goals

- No logic changes — pure structural reorganization
- No new abstractions or base classes
- No changes to templates or URLs
