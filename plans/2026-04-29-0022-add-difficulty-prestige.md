# Add Difficulty, Prestige, DNS/DNF, and Acquisition Price

## Current Schema (relevant tables)

```sql
races (id, firstcycling_race_id, name, year, num_stages, race_type, race_date, synced_at, pcs_slug, season_id)
athletes (id, firstcycling_id, full_name, nationality, team, last_synced_at, pcs_slug)
user_athletes (id, user_id, athlete_id, season_id)
race_results (id, race_id, athlete_id, position, points, result_type, stage_number, created_at, time)
```

---

## Migrations

### `20260429000007_enums.sql`
```sql
create type race_status    as enum ('ok', 'dns', 'dnf');
create type athlete_status as enum ('active', 'injured', 'paused');
```

### `20260429000008_difficulty_prestige.sql`
```sql
alter table races
  add column difficulty          smallint check (difficulty between 1 and 5),
  add column prestige            smallint check (prestige  between 1 and 5),
  add column difficulty_updated_at timestamptz,
  add column prestige_updated_at   timestamptz;
```

### `20260429000009_race_result_status.sql`
Also fixes `time` column from `text` → `interval`:
```sql
alter table race_results
  add column status race_status not null default 'ok',
  alter column position drop not null,
  alter column time type interval using time::interval;
```

### `20260429000010_athlete_status.sql`
Replaces two bool columns with a single enum:
```sql
alter table athletes
  add column status athlete_status not null default 'active';
```

### `20260429000011_acquisition_price.sql`
```sql
alter table user_athletes
  add column acquisition_price numeric(10,2) check (acquisition_price >= 0);
```

---

## Files to change

| File | Change |
|------|--------|
| `supabase/migrations/` | 5 new migration files above |
| `routers/admin.py` | Race form: difficulty + prestige (1–5); race_result form: status dropdown; athlete form: status dropdown (active/injured/paused); user_athlete form: acquisition price |
| `routers/dashboard.py` | Pass `difficulty`, `prestige` to races view; pass `status` to race results |
| `db_queries.py` | Include new columns in race, race_result, athlete, and user_athlete selects |
| `scoring.py` | Replace if-guard with dispatch table (see below) |
| `templates/admin/races.html` | Inputs for difficulty (1–5) and prestige (1–5) |
| `templates/admin/race_results.html` | Status dropdown: ok / dns / dnf |
| `templates/admin/athletes.html` | Status dropdown: active / injured / paused |
| `templates/admin/user_athletes.html` | Acquisition price input |
| `templates/dashboard/races.html` | Show difficulty and prestige badges |
| `templates/dashboard/index.html` | DNS/DNF indicator on leaderboard rows; acquisition price in user team view |
| `templates/dashboard/athlete.html` | Show athlete status (injured / paused) |

---

## Scoring rule

`scoring.py` — dispatch table, enums as keys:
```python
STATUS_POINTS = {
    'ok':  lambda r: base_points(r),
    'dnf': lambda r: 0,
    'dns': lambda r: 0,
}

def score_result(result):
    return STATUS_POINTS[result['status']](result)
```
