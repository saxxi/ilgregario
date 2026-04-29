# 0015 — Remove fake_data from Dashboard

**Goal:** Remove `fake_data` entirely from `routers/dashboard.py` and from
`db_queries.py`, always serving real Supabase data. Delete `fake_data.py`.

---

## Current state

- `routers/dashboard.py` toggles on `_USE_FAKE` env var; the `else` (real-DB)
  branch exists but is incomplete:
  - `race_labels` and `race_weekly_maxes` are derived from leaderboard dicts
    instead of calling the dedicated `db_queries` helpers
  - `narrative` (line 71) still calls `fake_data.get_season_narrative()` directly
- `db_queries.py` imports `fake_data` for two things:
  - `_rank_chart_data()` — pure SVG-path helper
  - `get_season_narrative()` — thin delegator back to `fake_data`
- `db_queries.get_race_labels()` and `get_race_weekly_maxes()` take internal
  data params (`season_id`, `completed`, `user_roster`, `race_pts`) — the
  dashboard route doesn't call them because it doesn't hold those params.

---

## Steps

### 1. Lift `_rank_chart_data` into `db_queries.py`

Copy the pure function from `fake_data.py` directly into `db_queries.py`
(it has no dependency on fake data). Remove the call to `fake_data._rank_chart_data`
in `get_user_detail()`.

### 2. Replace `get_season_narrative` delegation

Move the narrative logic from `fake_data.get_season_narrative()` into
`db_queries.get_season_narrative()` directly (it is pure Python, no DB calls).

### 3. Simplify `get_race_labels` / `get_race_weekly_maxes` in `db_queries.py`

These functions are only called from the dashboard route. Move them to be
computed inside a new helper `_build_race_chart_data(season_id)` that loads
everything it needs internally — matching the no-arg style of the other public
functions. Alternatively, make them no-arg by loading season data themselves.

### 4. Refactor `routers/dashboard.py`

- Remove `_USE_FAKE` flag and the `if _USE_FAKE / else` branches.
- Remove `import fake_data`.
- Always call `db_queries.*` functions.
- Replace the ad-hoc `race_labels` / `race_weekly_maxes` derivation with a
  dedicated `db_queries.get_race_chart_data()` call (returns `{labels, weekly_maxes}`).
- Call `db_queries.get_season_narrative()` for the narrative (no fake_data).

Target shape of the dashboard route (simplified):

```python
season      = db_queries._load_season()
leaderboard = db_queries.get_leaderboard()
recent_races = db_queries.get_recent_races(3)
top_athletes = db_queries.get_top_athletes()
next_race    = db_queries.get_next_race()
race_chart   = db_queries.get_race_chart_data()   # new helper
season_progress = db_queries.get_season_progress(season) if season else {}
...
narrative    = db_queries.get_season_narrative(leaderboard, races_done, races_total)
```

### 5. Remove `fake_data` import from `db_queries.py`

After steps 1–2, no symbol from `fake_data` should remain in `db_queries.py`.

### 6. Delete `fake_data.py`

Run a final `grep -r fake_data .` to confirm no remaining references, then
delete the file.

---

## Files changed

| File | Action |
|------|--------|
| `db_queries.py` | Add `_rank_chart_data`, inline narrative logic, add `get_race_chart_data()`, remove `import fake_data` |
| `routers/dashboard.py` | Remove `_USE_FAKE`, `import fake_data`; simplify to single db_queries path |
| `fake_data.py` | Delete |

---

## No template changes needed

All dict shapes returned by `db_queries` already match what templates expect
(same keys as the fake_data equivalents).
