# 0013 – Points showcase: dashboard & user page

**Goal**: Make the ranking pages something a fantaciclismo enthusiast dreams of.
Fake data only — no DB wiring in this plan.

---

## What enthusiasts want

- **Data at a glance**: who leads, by how much, race-by-race trend
- **Drama**: rank changes, hot streaks, nail-biting gaps
- **Depth**: athlete-level breakdown, head-to-head records
- **Context**: how each race changed the season narrative

---

## Dashboard (`/dashboard`) additions

### 1. Season narrative banner
One bold sentence that tells the story of the season so far.  
e.g. "Gregario88 in testa — solo 3 punti sopra CapoBranco dopo 4 gare".

### 2. Race-by-race points matrix
A responsive table: rows = users, columns = races + total.  
Each cell shows points scored that race (0 shown as `—`).  
Highlight the per-race winner (highest scorer that round).  
Users sorted by total descending.

### 3. Hot / cold streak pills in the leaderboard
After the username, a pill: 🔥 if scored in last 2 races, ❄️ if zero in last 2.

### 4. Top athletes of the season (sidebar card)
Independent of ownership: top 5 athletes by total points earned this season.  
Shows: athlete name, flag, team, total pts, best result badge.

### 5. Next race card
Shows the upcoming race with name, date, and which users have athletes that
historically perform there (teaser, faked).

---

## User page (`/users/{username}`) additions

### 1. Rank trajectory SVG line chart (replace / extend bar chart section)
Pure CSS/SVG, no JS. Shows rank position after each race (lower = better).
Plotted as a continuous line with dots.  
Overlays a faint "league average rank" line for context.

### 2. Head-to-head mini scorecards
For every other user: W / D / L record across the races played so far.  
A small card for each opponent showing win count, points differential.

### 3. Per-race mini-league rank
In the race history table, add a column: "Rank di gara" showing their finish
position among all users for that specific race (1st = won the weekly mini-league).

### 4. Athlete vs league average
On each athlete card: a small note comparing the athlete's points to the
league average for athletes in that position (e.g. "Sopra media: +3 pt").

### 5. Best / worst race highlights
Two callout boxes at the top of the race history section:  
best race (race name + pts) and worst race (race name or "—").

---

## Data additions (`fake_data.py`)

```
get_leaderboard()         → add streak, rank_history, per_race_pts list
get_recent_races()        → no change
get_top_athletes()        → new: top 5 athletes by season total pts
get_next_race()           → new: stub next race card
get_user_detail()         → add rank_history, h2h, per_race_rank
```

---

## Files to touch

| File | Change |
|---|---|
| `fake_data.py` | add new fields and helper functions |
| `routers/dashboard.py` | pass new context keys |
| `routers/dashboard.py` | pass new context keys to user_detail |
| `templates/dashboard/index.html` | add narrative, matrix, streaks, top-athletes, next-race |
| `templates/dashboard/user.html` | add rank chart, h2h, race rank col, athlete vs avg, best/worst |

---

## Order of implementation

1. `fake_data.py` — all new data
2. `routers/dashboard.py` — wire new data
3. `templates/dashboard/index.html` — new sections
4. `templates/dashboard/user.html` — new sections
