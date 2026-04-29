# Dashboard UI Polish

## Goal
Improve the visual quality and UX across all dashboard pages without changing data or routing.

## Changes

### base.html
- Active nav link highlighting based on current path (use JS to add `text-primary font-semibold` to matching link)
- Slightly taller nav for breathing room

### dashboard/index.html (Classifica)
- Hero header: add a subtle background gradient and a cycling icon accent
- Season stat cards: use a more polished two-column stat bar instead of floating stat cards
- Season narrative: wrap in a card with an icon prefix (💬 or 📣) and better typography
- Podium: add a subtle drop shadow and connecting "floor" bar beneath the three columns
- Leaderboard table: add row hover highlight with left border accent for top 3
- Catchability panel: tighten spacing, add visual win/loss color coding

### dashboard/races.html (Gare)
- Split into two explicit sections: **Completate** and **In arrivo** with a divider header
- Remove the opacity-50 approach (confusing on mobile) — upcoming races get a distinct "In arrivo" badge style
- Add a cycling flag icon to the page header

### dashboard/race.html (Race detail)
- Hero card: add a colored top border accent (primary for stage race, amber for one-day)
- User score cards: improve the layout of per-athlete rows — add subtle dividers and a total row

### dashboard/athlete.html (Athlete profile)
- Hero: use a slightly more prominent flag display
- Stat strip: center values look good — no major change needed
- Bar chart: add axis label for "pts" and a subtle dotted average line

### dashboard/user.html (Squad page)
- Hero: already the most polished page — minor spacing tweaks
- Rosa cards: show athlete status badge (injured/paused) on the card
- Acquisition price: if available, show in the rosa card footer
