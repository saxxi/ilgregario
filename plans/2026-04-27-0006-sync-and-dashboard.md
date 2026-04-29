# Sync data + show on dashboard

## Goal

Wire up the admin sync button and make the dashboard display real race data.

## Steps

1. **`routers/admin.py`** — add `POST /sync-races` that calls `sync()` and returns JSON
2. **`templates/admin/index.html`** — make "Sincronizza risultati" a form POSTing to `/sync-races`
3. **`routers/dashboard.py`** — query races + top-10 results + athlete names; pass to template
4. **`templates/dashboard/index.html`** — show athlete leaderboard + recent race results
5. Run `python scripts/sync_races.py` to populate DB
