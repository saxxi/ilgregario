# Athlete Photos Everywhere

## Goal
Show athlete photos wherever athletes appear in the UI, using the existing local images in `static/images/athletes/{pcs_slug}.png`.

## Current State
- `_athlete_photo_url()` exists in `db_queries.py` and is already used in `get_athlete_detail()`
- `athlete.html` already renders photos beautifully in the hero
- 221 athlete photos exist locally
- Other views that list athletes don't expose `photo_url`

## Places to Add Photos

### Backend (`db_queries.py`)
1. `_build_internal()` — add `photo_url` to the athletes dict so all downstream functions inherit it
2. `get_top_athletes()` missing-athletes fallback — add `photo_url`
3. `get_race_detail()` — add `photo_url` to each result row

### Frontend Templates

| Template | Location | Treatment |
|---|---|---|
| `dashboard/index.html` | Top Athletes sidebar (line 530) | Small circular photo (w-8 h-8) replacing the rank number, or alongside flag |
| `dashboard/user.html` | La Rosa athlete cards (line 182) | Small photo (w-10 h-10) in top-left of card |
| `dashboard/race.html` | Full Results Table, ATLETA column (line 178) | Tiny circular photo (w-8 h-8) next to flag+name |
| `dashboard/race.html` | Fantaciclo Scores, athlete rows (line 110) | Tiny photo (w-5 h-5) next to athlete name |

## Implementation Steps
1. Update `_build_internal()` to include `photo_url` in athletes dict
2. Update `get_top_athletes()` missing fallback to include `photo_url`
3. Update `get_race_detail()` to include `photo_url` in result rows
4. Update `dashboard/index.html` — Top Athletes sidebar
5. Update `dashboard/user.html` — La Rosa cards
6. Update `dashboard/race.html` — Results table and Scores section
