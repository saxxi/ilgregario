# 0014 — Real DB Dashboard + Season Countdown

**Goal:** Wire the dashboard to real Supabase data (replacing fake_data) and add a
season-progress widget showing time remaining and points still on the table.

---

## Migration

`20260428000006_races_season_id.sql`
- Add `season_id uuid references seasons(id)` (nullable) to `races`
- Update `sync_races.py` to resolve `season_id` from the active season before upsert

---

## New: `db_queries.py`

Mirrors every public function in `fake_data.py`, returns identical dict shapes so
templates need zero changes. Reads from Supabase:

```
seasons (active=true)
  → races (season_id)
  → user_athletes (season_id) → users, athletes
  → race_results (race_id in season's races, result_type=gc, stage_number=0)
```

Computation logic (rank history, h2h, streaks) is pure Python over the loaded data —
same maths as fake_data.py, no duplication of SQL.

---

## Router: `routers/dashboard.py`

Read `USE_FAKE_DATA` env var (default `"true"`).
Add to context: `season_progress` dict + `catchability` list.

---

## `fake_data.py`

Add `get_season_progress()` so the fake path provides the same new context keys.

---

## New dashboard sections (`templates/dashboard/index.html`)

### Season countdown strip
Between narrative and podium:
- Horizontal timeline: past race dots (filled) → next race (pulsing ring) → future (empty)
- Stats row: "Fine stagione · tra N giorni", "Prossima gara · tra N giorni", "~Xpt ancora in palio"

### Catchability panel
After the standings table:
- Green pill per non-leader: username + gap + ✓ if they can catch up (gap < max_pts_remaining)
- Label: "Stagione ancora aperta!" when all can catch or "Zona pericolo ✗" when not

---

## Season-progress context shape

```python
{
    "pct": 57,
    "races_done": 4,
    "races_total": 7,
    "days_to_end": 109,
    "season_end_str": "15 ago",
    "days_to_next": 11,
    "next_race_name": "Giro d'Italia",
    "next_race_short": "GIR",
    "max_pts_remaining": 176,   # sum of top-3 GC points for each upcoming race
    "timeline": [
        {"short": "MSR", "name": "Milano-Sanremo", "status": "done", "date": "22 mar"},
        ...
        {"short": "GIR", "name": "Giro d'Italia", "status": "next", "date": "9 mag"},
        ...
    ],
}
```

---

## Order of work

1. Migration file
2. `fake_data.get_season_progress()`
3. `db_queries.py` full implementation
4. `sync_races._upsert_race` — set season_id
5. `routers/dashboard.py` — USE_FAKE_DATA + new context keys
6. `templates/dashboard/index.html` — timeline strip + catchability panel
