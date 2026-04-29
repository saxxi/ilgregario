# 2026-04-29-0025 UX Improvements

## Changes

### 1. Timeline hover links
- Each race dot in the timeline strip links to `/races/{race.id}` (id already present in timeline data)
- Show race name as tooltip on hover

### 2. Linked usernames in narrative + catchability
- `get_season_narrative` returns `markupsafe.Markup` with `<a href="/users/{username}">` wrapping each username mention
- Same treatment for usernames in the Rimonta Possibile cards (`catchability`)

### 3. Admin: edit acquisition price inline
- New POST endpoint `POST /admin/users/{user_id}/athletes/{ua_id}/edit-price`
- Inline form in the price cell of `user_athletes.html` table

### 4. Season: budget + roster limits
- Migration `20260429000012_season_settings.sql`: add `total_budget int not null default 500`, `min_runners int not null default 9`, `max_runners int not null default 30` to `seasons`
- Extend create form with these three fields (defaults pre-filled)
- Add edit row per season to update the values
- Update `seasons_create` and new `seasons_edit` endpoints
