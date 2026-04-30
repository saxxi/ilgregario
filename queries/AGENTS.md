# queries/

Database query helpers. Every public function returns a dict (or list of dicts) shaped for templates.
The package is split by concern — add new functions to the file that owns that concern.

## Files

| File | What belongs here |
|---|---|
| `context.py` | `SeasonContext` dataclass, `load_season_context()`, raw DB loaders (`_load_*`), `_build_internal`, and helpers shared across dashboard and detail (`_user_race_points_list`, `_rank_history`, `_streak`) |
| `dashboard.py` | Queries that feed the main dashboard page and season overview: leaderboard, recent races, top athletes, next race, chart data, season narrative, season progress |
| `detail.py` | Queries that feed individual detail pages: user detail, race detail, athlete detail, all-races list, users-with-rosters list. Also owns helpers only used here (`_per_race_ranks`, `_rank_chart_data`) |
| `__init__.py` | Re-exports every public symbol — callers do `import queries` and get everything |

## Rules

- Public functions accept an optional `SeasonContext` to avoid redundant DB round-trips within a single request.
- Internal helpers are prefixed `_` and live in the same file as the public function(s) that use them. If a helper is needed by both `dashboard.py` and `detail.py`, move it to `context.py`.
- No template logic here — return plain dicts/lists/Markup only.
