# IlGregario: Agent Operating Guidelines

## Operational Protocol

1. **Mandatory Planning:** No code changes without a plan in `/plans/yyyy-mm-dd-000[n]-[title-kebab-case]`.
2. **Knowledge Updates:** Post-task, update relevant `AGENTS.md` files when architecture or edge cases change.
3. The aim of AGENTS.md is to work better with fewer tokens.

---

## Scoring System

All scoring lives in `config.py` (tables) and `scoring.py` (logic). Do not hardcode points anywhere else.

### How points are assigned

`gc_points(race_name, num_stages, position)` → resolves in this priority order:

1. **Named race** (`by_name` in `GC_SCORING`): Grand Tours top 15 (max 25pt), Monuments top 6 (max 10pt).
2. **Stage count** (`by_stages`): thresholds 1 / 4 / 8 / 14 / 999 stages.
3. **Default fallback**: `[3, 1]` (one-day race with no named rule).

`stage_points()` follows the same resolution but uses `STAGE_SCORING`. Currently only `gc` results are synced and displayed — stage points exist for future use.

`score_result(result_type, race_name, num_stages, position, status)` is the single entry point used by the admin form. DNS/DNF always = 0.

### What counts for fantasy scoring

Only `race_results` rows where `result_type = 'gc'` AND `stage_number = 0` are aggregated. A user's score for a race = sum of `points` for all their athletes in that race.

---

## Data Flow

```
PCS website
  └─ PCSImporter (importers/pcs.py)
       └─ scripts/sync_races.py  ←  also callable via POST /sync-races
            └─ DB (races + race_results + athletes)
                 └─ queries/  →  routers/  →  templates/
```

- Athletes are keyed by `pcs_slug` (PCS URL slug). `slug` is the URL-safe version used in routes.
- Athlete photos: `static/images/athletes/{pcs_slug}.png`. `utils.athlete_photo_url()` checks file existence.
- Season: only one `active = true` season at a time. All queries filter by the active season.
- `user_athletes` is the roster junction table (`user_id`, `athlete_id`, `season_id`, `acquisition_price`).

---

## Auth & Roles

- `users.role` values: `user` | `admin` | `super_admin`. `is_admin` column kept in sync for template compat.
- `super_admin` can only be created via `python -m scripts.create_super_admin` (CLI prompt).
- Admins can create/edit `user` and `admin` roles from the UI; `super_admin` is not assignable from UI.
- Session payload: `{ user_id, role, is_admin, username }`. `is_admin = role in (admin, super_admin)`.
- `create_session_token(user_id, role, username)` in `auth.py` — signature changed from `is_admin` bool to `role` str.
- **CSRF**: all admin POST forms include `<input type="hidden" name="_csrf" value="{{ csrf_token(session.user_id) }}">`. `csrf_token` is a Jinja2 global registered in `templates_env.py`. Validated in `_guard_post(request)` in `routers/admin/shared.py`.
- Logging: `logging.basicConfig(stream=sys.stdout)` in `main.py`. HTTP middleware logs every request. Admin errors use `logger.exception()` — never expose raw exception text to users.

### Required DB migration (run once in Supabase)

```sql
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS role text NOT NULL DEFAULT 'user'
  CHECK (role IN ('user', 'admin', 'super_admin'));

UPDATE users SET role = 'admin' WHERE is_admin = true;
```

---

## Where Things Live

| Concern | Location |
|---|---|
| Scoring tables | `config.py` — `GC_SCORING`, `STAGE_SCORING` |
| Scoring logic | `scoring.py` — `gc_points`, `score_result` |
| Session + CSRF helpers | `auth.py` |
| Jinja2 template instance + globals/filters | `templates_env.py` |
| Season context + DB loaders | `queries/context.py` |
| Dashboard queries | `queries/dashboard.py` |
| Detail page queries (user/race/athlete) | `queries/detail.py` |
| Admin routes by resource | `routers/admin/{overview,users,athletes,races,seasons}.py` |
| Dashboard + public routes | `routers/dashboard.py` |
| PCS scraper | `importers/pcs.py` |
| Race sync orchestrator | `scripts/sync_races.py` |
| Country data + flag emoji | `utils/countries.py` |
| Date/race formatting helpers | `utils/formatting.py` |
| Athlete photo URL | `utils/media.py` |
| slugify + AVATAR_COLORS | `utils/text.py` |
| Re-exports all of the above | `utils/__init__.py` (import as `import utils` or `from utils import X`) |

See `queries/AGENTS.md` and `routers/admin/AGENTS.md` for sub-package navigation.

---

## Development

### General
- Work locally; don't push to remote unless asked.
- DaisyUI + Tailwind for UI; minimal JS.

### On complex UI tasks
1. Prototype with plain HTML + hardcoded fake data.
2. Confirm data shape is sufficient.
3. Implement against real data on approval.

### Backend rules
- `SeasonContext` is loaded once per request and threaded through all query functions — never call `load_season_context()` twice in one request.
- To add a new scoring rule: edit `config.py` tables only; `scoring.py` logic is generic.
- New admin resource → new file in `routers/admin/`, register in `routers/admin/__init__.py`.
- New query concern → add to the appropriate `queries/` file per `queries/AGENTS.md`.
