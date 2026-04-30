# routers/admin/

FastAPI admin routes, split by resource. All routes require an admin session (`_guard`).
Add new routes to the file that owns that resource, or create a new file for a new resource.

## Files

| File | Routes |
|---|---|
| `shared.py` | `_guard(request)` — auth check, returns `(session, None)` or `(None, redirect)`. `_redir(path, msg)` — 303 redirect with optional flash. Shared `templates` instance. No routes. |
| `overview.py` | `GET /admin` — dashboard index. `POST /sync-races` — trigger race sync. |
| `users.py` | `GET/POST /admin/users` — list and create users. `GET /admin/users/{id}` — user detail with athlete assignments. `POST /admin/users/{id}/edit`, `/delete`. `POST /admin/users/{id}/athletes/add`, `/{ua_id}/delete`, `/{ua_id}/edit-price`. |
| `athletes.py` | `GET /admin/athletes` — list. `GET /admin/athletes/fc-fetch` — PCS/FirstCycling URL lookup (JSON). `POST /admin/athletes/create`, `/fetch-photos`, `/{id}/edit`, `/{id}/delete`. |
| `races.py` | `GET/POST /admin/races` — list and create. `POST /admin/races/{id}/edit`, `/{id}/delete`. `GET /admin/races/{id}/results` — results list. `POST /admin/races/{id}/results/add`, `/{id}/results/{res_id}/delete`. |
| `seasons.py` | `GET/POST /admin/seasons` — list and create. `POST /admin/seasons/{id}/edit`, `/{id}/activate`, `/{id}/delete`. |
| `__init__.py` | Combines all sub-routers into a single `router` exported for `main.py`. |

## Rules

- Every route handler must call `_guard(request)` first and return `err` if set.
- Use `_redir(path, msg)` for all POST redirects.
- Import `templates` from `.shared` — do not instantiate `Jinja2Templates` again.
- `__init__.py` is the only file that should call `router.include_router(...)`.
