# FirstCycling Athlete Import

**Date:** 2026-04-28
**Status:** Done

---

## Goal

When creating an athlete in the admin, the admin can paste a FirstCycling URL
(e.g. `https://firstcycling.com/rider.php?r=66973&y=2026`) and click a Fetch
button to auto-populate full_name, nationality, team, and firstcycling_id
before saving.

---

## Design

| Constraint | Consequence |
|---|---|
| No JS build step | Vanilla `fetch()` call from the create form |
| Existing `first_cycling_api` package | Reuse `fc.get_rider_endpoint()` for the HTTP call |
| Parsing gaps in existing code | `_get_sidebar_details` is a TODO stub — parse soup directly in the helper |

---

## New endpoint

`GET /admin/athletes/fc-fetch?url=<firstcycling_url>`

Returns JSON:
```json
{"full_name": "...", "nationality": "...", "team": "...", "firstcycling_id": 66973}
```

On parse failure, returns `{"error": "..."}` with HTTP 200 so JS can show a message.

### Parsing logic

| Field | Source |
|---|---|
| `firstcycling_id` | `r` query param from the pasted URL |
| `full_name` | `<h1>` text on the rider page |
| `nationality` | First flag `<img>` whose `src` contains `/flags/` in the sidebar/info area |
| `team` | Year-details table span that contains an `<img>` (team logo) |

---

## Template change

The "Aggiungi atleta" form gains a top row:

```
[FirstCycling URL input]  [Carica →]
```

On click, JS calls the endpoint, then fills `full_name`, `nationality`, `team`
inputs and sets a hidden `firstcycling_id` field. The admin can still edit the
pre-filled values before submitting.

---

## Route ordering

`GET /admin/athletes/fc-fetch` is a GET; all existing `/admin/athletes/…`
mutation routes are POST — no conflict.
