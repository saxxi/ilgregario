# Admin CRUD Scaffold — Users, Athletes, Races, Results

**Date:** 2026-04-27
**Status:** Done

---

## Context

The existing `/admin` page was a stub: one sync button, three dead links. This plan
wires up real management pages for every entity an admin needs to control manually —
both to seed data and to correct what the automated sync misses.

This is a private app for <10 users. The admin is a single trusted person.
That constraint shapes every decision below: we avoid complexity that only makes
sense for multi-admin or high-traffic scenarios.

---

## Design constraints

| Constraint | Consequence |
|---|---|
| Server-rendered Jinja2, no JS framework | All mutations are HTML form POSTs, not fetch/JSON |
| PicoCSS only, no custom CSS build step | Layout via inline `style=` grid; PicoCSS utility classes for buttons/tables |
| No JS build step | Edit modal uses native `<dialog>` + vanilla JS data attributes |
| Flash messages without a session store | `?msg=` query param on every redirect (URL-encoded) |
| Supabase-py client, no raw SQL | All mutations go through the table builder API |
| Single admin, no RBAC | `_guard()` helper checks `is_admin` on every handler; no role hierarchy |

---

## Auth guard

Every handler calls `_guard(request)` which returns `(session, None)` on success
or `(None, RedirectResponse("/login"))` on failure. The pattern is:

```python
session, err = _guard(request)
if err:
    return err
```

This avoids repeating the redirect logic in 15+ handlers and keeps the error path
explicit. The guard reads the signed session cookie via `auth.get_session()`.

For `POST /sync-races` specifically, the guard failure returns JSON 403 instead of
a redirect — that endpoint is called via `fetch()` from the browser, not a form.

---

## Template hierarchy

```
base.html                     ← top nav, PicoCSS link
└── admin/base.html           ← 2-col grid: sidebar nav | content slot
    ├── admin/index.html      ← sync button + JS fetch
    ├── admin/users.html      ← user table + create form
    ├── admin/athletes.html   ← athlete table + search + create form + edit <dialog>
    ├── admin/races.html      ← race table + manual create form
    └── admin/race_results.html ← results table + add-row form + recalc button
```

`admin/base.html` provides the sidebar and the flash message slot (`{{ msg }}`).
All admin templates extend it via `{% block admin_content %}`.

`admin/index.html` was reverted to extend `base.html` directly (not `admin/base.html`)
after the linter reset it — it does not use the sidebar because it is the sidebar's
"home" link destination and adding a redundant sidebar to it looked odd.

---

## Routes

### `/admin/users`

| Method | Path | Handler | Side effects |
|---|---|---|---|
| GET | `/admin/users` | `users_list` | None — reads `users` table |
| POST | `/admin/users/create` | `users_create` | Inserts row into `users`; hashes password with bcrypt |
| POST | `/admin/users/{user_id}/delete` | `users_delete` | Deletes user row; cascades to `user_athletes` via FK |

**Password hashing:** `auth.hash_password()` (bcrypt, 12 rounds). The admin
never sees plaintext passwords — they set the initial password and the user
changes it themselves (or doesn't, for this MVP).

**Self-delete:** not blocked. The admin is defined by env vars (`ADMIN_USERNAME` /
`ADMIN_PASSWORD`), not a DB row, so deleting a DB user does not lock out the admin.

**Missing:** no password-change route. Not needed for MVP; the admin can delete +
recreate a user if a password reset is needed.

### `/admin/athletes`

| Method | Path | Handler | Side effects |
|---|---|---|---|
| GET | `/admin/athletes` | `athletes_list` | Reads `athletes`; `?q=` does case-insensitive `ilike` on `full_name` |
| POST | `/admin/athletes/create` | `athletes_create` | Inserts row; `pcs_slug` stored as `NULL` if blank (DB allows multiple NULLs on the unique column) |
| POST | `/admin/athletes/{id}/edit` | `athletes_edit` | Updates `full_name`, `pcs_slug`, `nationality`, `team` |
| POST | `/admin/athletes/{id}/delete` | `athletes_delete` | Deletes athlete; cascades to `race_results` and `user_athletes` |

**Edit UX:** a native `<dialog>` element is shown when "Modifica" is clicked.
The JS reads `data-*` attributes from the button (set by Jinja2, HTML-escaped with
`| e`) to pre-fill the form, then sets `action` on the `<form>` to the correct
athlete ID before calling `showModal()`. No AJAX — the dialog just submits a
regular POST.

**Route ordering concern:** `POST /admin/athletes/create` and
`POST /admin/athletes/{athlete_id}/edit` share the `/admin/athletes/` prefix.
FastAPI matches literal path segments before path parameters, so `/create` will
never be mistakenly captured as `{athlete_id}`. The ordering in the router file
reinforces this.

**`pcs_slug` uniqueness:** the DB has a `UNIQUE` constraint on `athletes.pcs_slug`
but allows multiple NULLs (standard PostgreSQL behaviour). If the admin tries to
add a duplicate slug, the Supabase client raises an exception which is caught and
surfaced as `?msg=Errore: ...`.

### `/admin/races`

| Method | Path | Handler | Side effects |
|---|---|---|---|
| GET | `/admin/races` | `races_list` | Reads `races` ordered by `race_date DESC` |
| POST | `/admin/races/create` | `races_create` | Inserts a manually created race row |
| POST | `/admin/races/{id}/delete` | `races_delete` | Deletes race; cascades to `race_results` |

**Why manual race creation exists:** the PCS sync only pulls completed WT races.
Admins may want to add non-WT races or correct a name/date before results arrive.

**`synced_at` display:** shown as `YYYY-MM-DD HH:MM` (the `T` separator in the
ISO string is replaced in the template: `r.synced_at[:16].replace('T', ' ')`).
Races created manually have `synced_at = NULL`, shown as `—`.

**Race names → clicking opens results:** the race `name` in the table is a link
to `/admin/races/{id}/results`. This is the primary navigation into result entry.

### `/admin/races/{race_id}/results`

| Method | Path | Handler | Side effects |
|---|---|---|---|
| GET | `/admin/races/{id}/results` | `race_results_list` | Reads race, results, athlete names (3 queries) |
| POST | `/admin/races/{id}/results/add` | `race_results_add` | Inserts one result row |
| POST | `/admin/races/{id}/results/{r}/delete` | `race_results_delete` | Deletes one result row |

**Form fields:** athlete (required), result type (gc/stage), position (required),
stage number (optional, defaults to 0 per migration 0003), time (optional free text,
e.g. `4:12:35` or `+0:45`), points (optional — auto-calculated from `scoring.py`
if left blank, entered manually if provided).

**Point calculation:** `race_results_add` calls `scoring.gc_points()` or
`scoring.stage_points()` only when the points field is empty. If the admin types
a number, that value is used as-is. This covers overrides for races with non-standard
scoring or manual corrections.

**`stage_number` semantics:** `0` means "no specific stage" (used for GC results
and for stage results where the stage number is not tracked). Migration 0003 made
the column NOT NULL with default 0 and added the unique constraint
`(race_id, athlete_id, result_type, stage_number)`.

**`time` column:** added in migration 0004 as `text` (nullable). Free-form string —
no parsing enforced. Stored and displayed as entered.

**No duplicate protection:** `race_results` has no unique constraint on
`(race_id, athlete_id, result_type, stage_number)` at the application level for
admin-entered data. The sync script uses `on_conflict=` upsert, but the admin
form uses a plain insert. If the admin adds the same athlete+race+type twice,
both rows will exist and both count toward scoring. This is intentional — the
admin should be trusted to not do this, and adding a constraint would require a
new migration.

**3-query pattern on results page:** (1) fetch race, (2) fetch results for race,
(3) fetch athlete names for those result rows. A fourth query fetches all athletes
for the "add result" dropdown. Acceptable for a page with <100 rows.

---

## Flash messages

Every mutating handler ends with `_redir(path, msg)`. The `_redir` helper
appends `?msg=<url-encoded string>` to the redirect URL. The receiving GET handler
accepts `msg: str = ""` as a query param and passes it to the template.
`admin/base.html` renders `{{ msg }}` inside a `<mark>` element if non-empty.

This avoids a server-side session store for flash messages, at the cost of the
message being visible in the browser URL bar briefly.

---

## What is NOT in this plan

| Feature | Why excluded |
|---|---|
| User–athlete assignment UI (`user_athletes`) | Needs season context; deferred to a separate plan |
| Season management | Season is currently seeded once; no multi-season UI needed yet |
| Race edit form | Name/date fixes can be done via manual delete + re-create; low priority |
| Pagination on lists | <200 rows expected; hard limit in queries is sufficient |
| Optimistic locking | Single admin, no concurrent edits expected |
| CSRF tokens | FastAPI does not provide them out of the box; itsdangerous session cookie provides replay-resistance for now |
