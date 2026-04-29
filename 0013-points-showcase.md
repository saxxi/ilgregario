# 0013 – Points Showcase: Dashboard & User Page *(revised)*

**Goal**: Make the ranking pages something a fantaciclismo enthusiast dreams of.
Fake data only — no DB wiring in this plan.

---

## What enthusiasts actually want

- **Instant drama**: who's leading, who's closing the gap, who just had a disaster race
- **Cyclist identity**: they're *team owners* — make their roster feel like theirs
- **Race narrative**: each Monument has a story; reflect it in the UI
- **Rivalry**: head-to-head is the fuel of every fantasy league conversation
- **Anticipation**: the next race feels like it matters

---

## Dashboard (`/dashboard`)

### 1. Season narrative banner *(keep, improve copy)*
One bold sentence, but make it dynamic and spicy — surface the most *interesting* thing, not just the leader. Priority order:

1. Gap closed by ≥5 pts in last race → "CapoBranco risale: solo 3 punti dal leader"
2. Tie at the top → "Pareggio in vetta dopo la Roubaix — tutto da decidere"
3. Dominant leader → "Gregario88 scappa: +8 sul secondo dopo 4 gare"

### 2. Race-by-race points matrix *(keep)*
Rows = users sorted by total, columns = races + total. Additions:
- Per-race winner cell gets a 🏆 badge, not just highlighting
- Zero-point cells show `—` in muted grey (not bold zero)
- A **"Δ last"** column showing points gained/lost vs. race before (signed, colored)
- Sticky first column on mobile

### 3. Leaderboard: richer row treatment *(upgrade streak pills)*
Replace simple 🔥/❄️ with a mini sparkline (3-bar SVG, pure CSS) showing last 3 races inline. Also add:
- **Gap to leader** shown as `-8 pt` in muted text (not just rank number)
- **"Maglia virtuale"** icon 🟡 next to whoever leads at this moment (like the yellow jersey)
- Color-code rank change: ↑ green, ↓ red, = grey

### 4. Top athletes of the season *(keep, add ownership context)*
Top 5 athletes by points. Crucially: show **who owns them** — this is the fantasy hook. If an athlete is unowned, show "senza padrone 👻". Add `get_top_athletes()` to `fake_data.py`.

### 5. Race timeline strip *(replace "next race card" with a full season arc)*
A horizontal strip of all races: past ones show the winner emoji + short name, the next one pulses with a 🔜 badge, future ones are greyed out. Far more useful than a single next-race card and gives season context at a glance. One component, zero JS.

### 6. "Chi rischia?" alert card *(new)*
A small callout: the user in 2nd place and how many points they need to overtake the leader. Creates tension even mid-season. Simple derived stat from `get_leaderboard()`.

---

## User page (`/users/{username}`)

### 1. Rank trajectory chart *(keep, specify more carefully)*
SVG line chart, rank after each race (y-axis inverted: 1 at top). Plot:
- User's rank line — solid, colored
- League average — dashed grey
- Each dot labeled with race short name
- Annotate biggest rank jump: a callout bubble "↑ 2 dopo ROU"

One important fix vs. the original plan: **`rank_history` must be added to `get_user_detail()` as a list of rank integers**, one per completed race, computed by calling `get_leaderboard()` after each race subset. Add `_leaderboard_after_race(n)` helper in `fake_data.py`.

### 2. Head-to-head mini scorecards *(keep, make it a table not cards)*
Cards won't scale with 6 users — use a compact table instead:

| Avversario | V | P | S | Diff pts |
|---|---|---|---|---|
| CapoBranco | 3 | 0 | 1 | +5 |

Sort by points differential descending. Color the diff column. This is more scannable and fits on mobile.

### 3. Per-race mini-league rank column *(keep)*
In the race table: add "Rank di gara" column. Derive from `get_user_detail()` — add `per_race_rank` list to the races detail. 1st = 🥇, 2nd = 🥈, 3rd = 🥉, others = plain number.

### 4. Athlete cards: richer stats *(upgrade "vs avg" idea)*
Each athlete card should show:
- Points per race they've completed (not just total) — "7.0 pt/gara"
- Vs. league avg for athletes in that slot: `+3 vs media` or `-1 vs media`
- A mini race-by-race dot row (filled = scored, empty = DNS/not placed) — pure CSS, 4 dots

The "vs avg" needs a new helper: `get_league_avg_by_slot()` — average points per roster position (slot 1/2/3) across all users. This is more meaningful than a flat average.

### 5. Best / worst race callouts *(keep, extend)*
Add a third callout: **"Gara chiave"** — the race where this user gained the most ground on the current leader. More interesting than just raw best score.

### 6. Team header card *(new)*
At the very top of the user page: a "squad card" showing all 3 athletes side by side with flag, team, total pts, and a status badge:
- 🔥 Hot (scored in last 2 races)
- 😴 Cold (0 in last 2)
- ⭐ Star (top 5 athlete overall)

This reinforces the *team owner* fantasy identity immediately on page load.

---

## Data layer additions (`fake_data.py`)

```python
# Existing — extend return value
get_leaderboard()      → add: streak (int, positive=hot), rank_history, per_race_pts, gap_to_leader
get_user_detail()      → add: rank_history, h2h (dict), per_race_rank, per_race_rank_labels, best_race, worst_race, key_race

# New functions
get_top_athletes()             → top 5 athletes by season pts, with owner username
get_season_timeline()          → all races with status (done/next/upcoming), winner per done race
get_league_avg_by_slot()       → avg pts for roster slot 1, 2, 3 across all users
_leaderboard_after_race(n)     → internal: standings after first n races (for rank_history)
_h2h(username)                 → W/D/L + pt diff vs each other user, per race
```

All additions are pure Python over the existing `_RACE_RESULTS` / `_USER_ATHLETES` dicts — no new constants needed.

---

## Files to touch

| File | Change |
|---|---|
| `fake_data.py` | new helpers + extended return values |
| `routers/dashboard.py` | wire `get_top_athletes()`, `get_season_timeline()` to dashboard context |
| `routers/users.py` | wire enriched `get_user_detail()` |
| `templates/dashboard/index.html` | narrative, matrix (+Δ col), leaderboard upgrades, top-athletes, timeline strip, "chi rischia" |
| `templates/dashboard/user.html` | team header card, rank SVG chart, h2h table, race rank col, athlete dots, best/worst/key race |
| `templates/components/sparkline.html` | reusable 3-bar mini sparkline (used in leaderboard rows) |

Extract the sparkline as a Jinja2 macro — it'll be reused in both the leaderboard and athlete cards.

---

## Order of implementation

1. **`fake_data.py`** — all new data, test with `python -c "from fake_data import *; print(get_user_detail('Gregario88'))"`
2. **`routers/`** — wire new context keys, no template changes yet; verify data flows through
3. **`templates/dashboard/index.html`** — narrative → matrix → leaderboard → timeline → sidebar
4. **`templates/dashboard/user.html`** — team header → rank chart → h2h → race table → athlete cards
5. **`templates/components/sparkline.html`** — extract macro once it appears in both templates

---

## What got cut vs. original plan and why

| Original idea | Decision |
|---|---|
| 🔥/❄️ streak pills | Replaced by sparkline — more information, same space |
| "Next race card" alone | Absorbed into full season timeline strip — more context |
| Athlete cards as layout for h2h | Switched to table — scales better with 6 users |
| Flat "vs league avg" | Changed to per-slot average — more meaningful for fantasy |
