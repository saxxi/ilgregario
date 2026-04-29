# Athlete Slug Routing

## Goal
Replace UUID-based athlete routes with human-readable slugs.
- Primary: `pcs_slug` (already populated for most athletes)
- Fallback: slugified `full_name` (e.g. "Albèrt Eìnstéin" → "albert-einstein")

## Steps

1. **Migration**: add `slug text unique not null` to `athletes`
   - Enable `unaccent` extension
   - Populate existing rows: `COALESCE(pcs_slug, slugify(full_name))`
   - Slugify SQL: `lower(regexp_replace(unaccent(full_name), '[^a-z0-9]+', '-', 'g'))`
   - Trim leading/trailing hyphens

2. **Collision check**: verify no two athletes produce the same slug in current data (run as part of migration; fail loudly if collision found)

3. **Python slug helper** in `db_queries.py`
   - `slugify(name: str) -> str` using `unicodedata.normalize` + regex — used when inserting new athletes

4. **Update `get_athlete_detail`**: look up by `slug` column instead of `id`

5. **Update route**: `main.py` `/athletes/{athlete_id}` → `/athletes/{slug}`

6. **Update athlete importer**: compute and store `slug` on insert (prefer `pcs_slug`, fallback to name slug, handle collision with `-2` suffix)

7. **Update all internal links**: any template or query that builds `/athletes/{id}` links must switch to `/athletes/{slug}`
