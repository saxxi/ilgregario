# User–Athlete Assignments

**Date:** 2026-04-28
**Status:** Done

---

## Goal

Clicking a user in `/admin/users` opens `/admin/users/{user_id}` where the
admin can see and edit which athletes are assigned to that user for a given
season.

---

## Seasons

`user_athletes` requires a `season_id`. Seasons are currently unseeded.
Rather than a separate seasons admin page, we handle them inline on the user
detail page:

- If no seasons exist → show a one-line create form instead of the assignment table.
- If seasons exist → show a `<select>` to pick the active season; default to
  the one where `active = true`, or the first one.

A "Crea stagione" form collects `name` and `year` (and optional `active`).
`POST /admin/seasons/create` handles this.

---

## Routes

| Method | Path | Handler | Notes |
|---|---|---|---|
| GET | `/admin/users/{user_id}` | `user_detail` | Loads user, seasons, assignments for selected season |
| POST | `/admin/seasons/create` | `seasons_create` | Creates season; redirects back to user page |
| POST | `/admin/users/{user_id}/athletes/add` | `user_athletes_add` | Adds one assignment |
| POST | `/admin/users/{user_id}/athletes/{ua_id}/delete` | `user_athletes_delete` | Removes one assignment |

---

## Template

`admin/user_athletes.html` extending `admin/base.html`:

- Breadcrumb: Utenti → {username}
- Season picker `<select>` (GET form, `?season_id=`)
- Table of current assignments for selected season
- "Aggiungi atleta" `<select>` (only athletes not already assigned)
- Inline "Crea stagione" form shown when no seasons exist

---

## Users list change

Username in `admin/users.html` becomes a link: `<a href="/admin/users/{{ u.id }}">{{ u.username }}</a>`
