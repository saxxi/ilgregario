# 0010 — Athlete unique per season (one owner per athlete)

## Goal
Once an athlete is assigned to any user in a season, prevent assigning them to another user in the same season.

## Changes

### 1. Migration: add unique constraint on (athlete_id, season_id)
- New file: `supabase/migrations/20260428000005_user_athletes_unique_per_season.sql`
- `ALTER TABLE user_athletes ADD CONSTRAINT user_athletes_athlete_season_unique UNIQUE (athlete_id, season_id);`

### 2. router: user_athletes_add — pre-check + friendly error
- Before insert, query whether `athlete_id` is already assigned in `season_id` (to any user)
- If taken, redirect with Italian error message naming the existing owner

### 3. router: user_detail — pass taken_athlete_ids to template
- Query all `user_athletes` for the selected season (not just this user's)
- Pass `taken_athlete_ids = set of athlete_ids assigned to OTHER users` to the template

### 4. template: user_athletes.html — disable taken athletes in dropdown
- Render taken athletes as `<option disabled>` with "(già assegnato)" label so admin can see but not select them
