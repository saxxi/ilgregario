# 0011 — User Points Dashboard

**Goal:** Build the core fantasy experience: a season leaderboard of fantasy users (not raw athletes) and a rich per-user detail page that makes a fantaciclismo enthusiast want to stare at it all day.

---

## What we're building

### 1. Dashboard `/dashboard` — Classifica Stagione

Currently shows raw athlete points. Replace with a **fantasy-user leaderboard** — who is winning the game.

Sections:
- **Podio** — top-3 fantasy users on a visual podium (2nd–1st–3rd heights)
- **Classifica completa** — full standings table: rank, avatar/initials, username, total points, progress bar relative to leader, gap (Δ), points earned in last race, trend arrow
- **Ultime gare** — last 2-3 races as event cards: which of your users' athletes scored, winner highlight, points per user

### 2. User detail `/users/{username}` — Pagina atleta fantasy

Header stat strip: rank badge, total points (XL), gap from leader, best race result.

Then:
- **Rosa** — grid of athlete cards: name, team, nationality flag emoji, total points for season, best single result ("🥇 MSR", "🥈 LBL")
- **Classifica per gara** — table of every completed race: race name, which athlete scored, position, points; totals row at bottom
- **Grafici punti** — CSS bar chart (no JS) showing cumulative points race-by-race

### 3. Fake data (`fake_data.py`)

Toggle via a `USE_FAKE_DATA = True` env flag (default True when `DEBUG=true`). Provides:
- 6 fantasy users with Italian cycling-fan nicknames
- 18 pro cyclists (real current roster: Pogačar, Vingegaard, Evenepoel, van der Poel…)
- 3 athletes per user
- 4 completed spring classics (Milano-Sanremo, Fiandre, Roubaix, LBL) with realistic results
- Pre-calculated user totals and per-race breakdowns

---

## Data model (no migration needed)

All queries join: `users → user_athletes → athletes → race_results → races`

User total points = `SUM(race_results.points)` for all athletes belonging to that user in the active season.

Fake data mirrors this shape exactly so templates work identically against real DB.

---

## Files changed

| File | Action |
|---|---|
| `fake_data.py` | New — rich fake season data |
| `routers/dashboard.py` | Replace dashboard query; add `/users/{username}` route |
| `templates/dashboard/index.html` | Full redesign — podium + standings + race cards |
| `templates/dashboard/user.html` | New — per-user detail page |
| `templates/base.html` | Minor — add Users link in navbar if logged in |

---

## Design system

DaisyUI v4 + Tailwind CDN (no build step). Key components:
- `stat` / `stats` for metric strips
- `card` for race event cards and athlete cards in the roster
- `avatar` (placeholder) with initials fallback for user avatars
- `progress` bar for points relative to leader
- `badge` for rank, trend arrows, nationality
- `table` for standings and race history
- CSS-only bar chart using flex + `height` inline style

Colour conventions:
- Gold `text-yellow-500` / `bg-yellow-50` for #1
- Silver `text-gray-400` for #2
- Bronze `text-amber-600` for #3
- `badge-success` / `badge-error` for trend up/down
