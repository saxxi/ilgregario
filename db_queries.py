"""
Database query helpers for the fantasy leaderboard.
Every function returns the same dict shape that templates expect.
"""

import os
import re
import unicodedata
from datetime import date, datetime, timezone
from markupsafe import Markup, escape
from database import get_db
from scoring import gc_points


def _slugify(name: str) -> str:
    nfkd = unicodedata.normalize('NFKD', name)
    ascii_str = nfkd.encode('ascii', 'ignore').decode('ascii')
    slug = re.sub(r'[^a-z0-9]+', '-', ascii_str.lower())
    return slug.strip('-')

_ATHLETE_PHOTO_DIR = os.path.join(os.path.dirname(__file__), "static", "images", "athletes")


def _athlete_photo_url(pcs_slug: str) -> str | None:
    if not pcs_slug:
        return None
    path = os.path.join(_ATHLETE_PHOTO_DIR, f"{pcs_slug}.png")
    return f"/static/images/athletes/{pcs_slug}.png" if os.path.isfile(path) else None


# ---------------------------------------------------------------------------
# Nationality → flag emoji (best-effort)
# ---------------------------------------------------------------------------

_FLAG = {
    "Slovenia": "🇸🇮", "Denmark": "🇩🇰", "Belgium": "🇧🇪", "Netherlands": "🇳🇱",
    "France": "🇫🇷", "Spain": "🇪🇸", "Colombia": "🇨🇴", "Italy": "🇮🇹",
    "Australia": "🇦🇺", "Great Britain": "🇬🇧", "United Kingdom": "🇬🇧",
    "Norway": "🇳🇴", "Germany": "🇩🇪", "Portugal": "🇵🇹", "Eritrea": "🇪🇷",
    "Ecuador": "🇪🇨", "United States": "🇺🇸", "Switzerland": "🇨🇭",
    "Ireland": "🇮🇪", "Poland": "🇵🇱", "Kazakhstan": "🇰🇿",
}
_AVATAR_COLORS = ["primary", "secondary", "accent", "success", "error", "warning"]


def _flag(nationality: str | None) -> str:
    return _FLAG.get(nationality or "", "")


# ---------------------------------------------------------------------------
# Internal data loaders
# ---------------------------------------------------------------------------

def _load_season():
    db = get_db()
    rows = db.table("seasons").select("*").eq("active", True).limit(1).execute().data
    return rows[0] if rows else None


def _load_races(season_id: str) -> list[dict]:
    return (
        get_db()
        .table("races")
        .select("*")
        .eq("season_id", season_id)
        .order("race_date")
        .execute()
        .data
    )


def _load_user_athletes(season_id: str) -> list[dict]:
    return (
        get_db()
        .table("user_athletes")
        .select("id,user_id,athlete_id,acquisition_price,users(id,username),athletes(id,full_name,team,nationality,pcs_slug,slug,status)")
        .eq("season_id", season_id)
        .execute()
        .data
    )


def _load_results(race_ids: list[str]) -> list[dict]:
    if not race_ids:
        return []
    return (
        get_db()
        .table("race_results")
        .select("*")
        .in_("race_id", race_ids)
        .eq("result_type", "gc")
        .eq("stage_number", 0)
        .execute()
        .data
    )


# ---------------------------------------------------------------------------
# Internal computation helpers
# ---------------------------------------------------------------------------

def _build_internal(races, ua_rows, result_rows):
    """
    Reshape DB rows into the same internal format used throughout:
      user_roster : {username: [athlete_id, ...]}
      athletes    : {athlete_id: {full_name, team, flag}}
      race_pts    : {race_id: {athlete_id: {position, points}}}
    Returns (completed_races, upcoming_races, user_roster, athletes, race_pts).
    """
    today = date.today()

    user_roster: dict[str, list[str]] = {}
    athletes: dict[str, dict] = {}

    for ua in ua_rows:
        username = ua["users"]["username"]
        ath = ua["athletes"]
        aid = ath["id"]
        if username not in user_roster:
            user_roster[username] = []
        user_roster[username].append(aid)
        if aid not in athletes:
            pcs_slug = ath.get("pcs_slug") or ""
            athletes[aid] = {
                "id": aid,
                "full_name": ath["full_name"],
                "team": ath.get("team") or "",
                "flag": _flag(ath.get("nationality")),
                "pcs_slug": pcs_slug,
                "slug": ath.get("slug") or _slugify(ath["full_name"]),
                "status": ath.get("status", "active"),
                "photo_url": _athlete_photo_url(pcs_slug),
            }

    race_pts: dict[str, dict[str, dict]] = {}
    for rr in result_rows:
        rid = rr["race_id"]
        aid = rr["athlete_id"]
        if rid not in race_pts:
            race_pts[rid] = {}
        race_pts[rid][aid] = {"position": rr["position"], "points": rr["points"], "status": rr.get("status", "ok")}

    completed = [r for r in races if r.get("race_date") and r["race_date"] <= str(today)]
    upcoming  = [r for r in races if not r.get("race_date") or r["race_date"] > str(today)]

    return completed, upcoming, user_roster, athletes, race_pts


def _user_race_points_list(username, completed, user_roster, race_pts) -> list[int]:
    athlete_ids = user_roster.get(username, [])
    return [
        sum(race_pts.get(r["id"], {}).get(a, {}).get("points", 0) for a in athlete_ids)
        for r in completed
    ]


def _user_total_up_to(username, completed, user_roster, race_pts, n) -> int:
    athlete_ids = user_roster.get(username, [])
    return sum(
        sum(race_pts.get(r["id"], {}).get(a, {}).get("points", 0) for a in athlete_ids)
        for r in completed[:n]
    )


def _rank_history(username, usernames, completed, user_roster, race_pts) -> list[int]:
    hist = []
    for i in range(len(completed)):
        scores = {u: _user_total_up_to(u, completed, user_roster, race_pts, i + 1) for u in usernames}
        sorted_u = sorted(scores, key=lambda u: (-scores[u], u))
        hist.append(sorted_u.index(username) + 1)
    return hist


def _per_race_ranks(username, usernames, completed, user_roster, race_pts) -> list[int]:
    ranks = []
    for r in completed:
        scores = {
            u: sum(race_pts.get(r["id"], {}).get(a, {}).get("points", 0)
                   for a in user_roster.get(u, []))
            for u in usernames
        }
        sorted_u = sorted(scores, key=lambda u: (-scores[u], u))
        ranks.append(sorted_u.index(username) + 1)
    return ranks


def _streak(per_race: list[int]) -> str:
    if len(per_race) < 2:
        return "neutral"
    last2 = per_race[-2:]
    if all(p > 0 for p in last2):
        return "hot"
    if all(p == 0 for p in last2):
        return "cold"
    return "neutral"


def _race_short(race: dict) -> str:
    name = race["name"]
    return "".join(w[0] for w in name.split()[:3]).upper()[:3]


def _fmt_date(race: dict) -> str:
    if not race.get("race_date"):
        return ""
    d = date.fromisoformat(race["race_date"])
    _months = ["", "gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
    return f"{d.day} {_months[d.month]}"


def _rank_chart_data(rank_history: list[int], race_labels: list[str], num_users: int) -> dict:
    n = len(rank_history)
    if n == 0:
        return {"points": "", "dots": [], "y_labels": [], "chart_w": 500, "chart_h": 120}

    x_from, x_to = 50, 470
    y_from, y_to = 15, 82

    def x_for(i: int) -> int:
        if n == 1:
            return (x_from + x_to) // 2
        return x_from + int((x_to - x_from) * i / (n - 1))

    def y_for(r: int) -> int:
        if num_users <= 1:
            return (y_from + y_to) // 2
        return y_from + int((y_to - y_from) * (r - 1) / (num_users - 1))

    dots = [
        {
            "x": x_for(i),
            "y": y_for(r),
            "rank": r,
            "label": race_labels[i] if i < len(race_labels) else str(i + 1),
            "is_last": i == n - 1,
        }
        for i, r in enumerate(rank_history)
    ]
    y_labels = [{"rank": r, "y": y_for(r)} for r in range(1, num_users + 1)]
    return {
        "points": " ".join(f"{d['x']},{d['y']}" for d in dots),
        "dots": dots,
        "y_labels": y_labels,
        "chart_w": 500,
        "chart_h": 120,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_leaderboard() -> list[dict]:
    season = _load_season()
    if not season:
        return []

    races = _load_races(season["id"])
    ua_rows = _load_user_athletes(season["id"])
    results = _load_results([r["id"] for r in races])
    completed, _, user_roster, athletes, race_pts = _build_internal(races, ua_rows, results)

    if not user_roster:
        return []

    usernames = list(user_roster.keys())

    rows = []
    for username in usernames:
        per_race = _user_race_points_list(username, completed, user_roster, race_pts)
        total = sum(per_race)
        last  = per_race[-1] if per_race else 0
        prev  = per_race[-2] if len(per_race) >= 2 else 0
        trend = "up" if last > prev else ("down" if last < prev else "same")
        hist  = _rank_history(username, usernames, completed, user_roster, race_pts)
        rows.append({
            "username": username,
            "total": total,
            "last": last,
            "trend": trend,
            "streak": _streak(per_race),
            "per_race_pts": per_race,
            "rank_history": hist,
        })

    rows.sort(key=lambda x: (-x["total"], x["username"]))
    max_pts   = rows[0]["total"] if rows else 1
    leader_pts = rows[0]["total"] if rows else 0

    result = []
    for i, row in enumerate(rows):
        result.append({
            "rank": i + 1,
            "username": row["username"],
            "initials": row["username"][:2].upper(),
            "total_points": row["total"],
            "gap": 0 if i == 0 else row["total"] - leader_pts,
            "last_race_points": row["last"],
            "trend": row["trend"],
            "streak": row["streak"],
            "per_race_pts": row["per_race_pts"],
            "rank_history": row["rank_history"],
            "pct": int(row["total"] / max_pts * 100) if max_pts else 0,
            "color": _AVATAR_COLORS[i % len(_AVATAR_COLORS)],
        })
    return result


def get_race_labels(season_id: str, completed: list[dict]) -> list[str]:
    return [_race_short(r) for r in completed]


def get_race_weekly_maxes(usernames, completed, user_roster, race_pts) -> list[int]:
    result = []
    for r in completed:
        maxp = max(
            (sum(race_pts.get(r["id"], {}).get(a, {}).get("points", 0) for a in user_roster.get(u, []))
             for u in usernames),
            default=0,
        )
        result.append(maxp)
    return result


def get_race_chart_data() -> dict:
    season = _load_season()
    if not season:
        return {"labels": [], "weekly_maxes": []}
    races = _load_races(season["id"])
    ua_rows = _load_user_athletes(season["id"])
    results = _load_results([r["id"] for r in races])
    completed, _, user_roster, _, race_pts = _build_internal(races, ua_rows, results)
    usernames = list(user_roster.keys())
    labels = [_race_short(r) for r in completed]
    weekly_maxes = get_race_weekly_maxes(usernames, completed, user_roster, race_pts)
    return {"labels": labels, "weekly_maxes": weekly_maxes}


def get_recent_races(n: int = 3) -> list[dict]:
    season = _load_season()
    if not season:
        return []

    races = _load_races(season["id"])
    ua_rows = _load_user_athletes(season["id"])
    results = _load_results([r["id"] for r in races])
    completed, _, user_roster, athletes, race_pts = _build_internal(races, ua_rows, results)

    recent = list(reversed(completed))[:n]
    out = []
    for race in recent:
        scores = []
        for username, athlete_ids in user_roster.items():
            r_results = race_pts.get(race["id"], {})
            user_results = [
                {
                    "athlete": athletes[a]["full_name"],
                    "position": r_results[a]["position"],
                    "points": r_results[a]["points"],
                }
                for a in athlete_ids if a in r_results
            ]
            user_results.sort(key=lambda r: r["position"])
            pts = sum(r["points"] for r in user_results)
            if pts > 0:
                scores.append({"username": username, "points": pts, "results": user_results})
        scores.sort(key=lambda s: -s["points"])
        out.append({
            "race": {
                "id": race["id"],
                "name": race["name"],
                "short": _race_short(race),
                "date": _fmt_date(race),
                "race_type": race["race_type"],
                "race_date": race.get("race_date", ""),
                "pcs_slug": race.get("pcs_slug", ""),
                "year": race.get("year", 2026),
            },
            "scores": scores,
        })
    return out


def get_top_athletes() -> list[dict]:
    season = _load_season()
    if not season:
        return []

    races = _load_races(season["id"])
    ua_rows = _load_user_athletes(season["id"])
    results = _load_results([r["id"] for r in races])
    completed, _, user_roster, athletes, race_pts = _build_internal(races, ua_rows, results)

    athlete_owner: dict[str, str] = {}
    for username, aids in user_roster.items():
        for aid in aids:
            athlete_owner[aid] = username

    scores: dict[str, int] = {}
    best: dict[str, tuple] = {}
    for race in completed:
        short = _race_short(race)
        for aid, res in race_pts.get(race["id"], {}).items():
            scores[aid] = scores.get(aid, 0) + res["points"]
            if aid not in best or res["position"] < best[aid][0]:
                best[aid] = (res["position"], short)

    ranked = sorted(scores, key=lambda a: -scores[a])[:5]

    # Load profiles for athletes in results but not in any user's roster
    missing = [aid for aid in ranked if aid not in athletes]
    if missing:
        rows = (
            get_db()
            .table("athletes")
            .select("id,full_name,team,nationality,pcs_slug,slug")
            .in_("id", missing)
            .execute()
            .data
        )
        for r in rows:
            pcs_slug = r.get("pcs_slug") or ""
            athletes[r["id"]] = {
                "id": r["id"],
                "full_name": r["full_name"],
                "team": r.get("team") or "",
                "flag": _flag(r.get("nationality")),
                "pcs_slug": pcs_slug,
                "slug": r.get("slug") or _slugify(r["full_name"]),
                "photo_url": _athlete_photo_url(pcs_slug),
            }

    result = []
    for rank, aid in enumerate(ranked, 1):
        ath = athletes.get(aid, {"id": aid, "full_name": "—", "team": "", "flag": "", "pcs_slug": "", "slug": aid})
        br = best.get(aid, (None, None))
        pos_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(br[0], f"{br[0]}°" if br[0] else "—")
        result.append({
            "rank": rank,
            "id": aid,
            "full_name": ath["full_name"],
            "team": ath["team"],
            "flag": ath["flag"],
            "pcs_slug": ath.get("pcs_slug", ""),
            "slug": ath.get("slug") or _slugify(ath["full_name"]),
            "photo_url": ath.get("photo_url") or _athlete_photo_url(ath.get("pcs_slug", "")),
            "total_points": scores[aid],
            "best": f"{pos_emoji} {br[1]}" if br[1] else "—",
            "owner": athlete_owner.get(aid, "—"),
        })
    return result


def get_next_race() -> dict:
    season = _load_season()
    if not season:
        return {}
    races = _load_races(season["id"])
    today = str(date.today())
    upcoming = [r for r in races if r.get("race_date", "") > today]
    if not upcoming:
        return {}
    r = upcoming[0]
    return {
        "id": r["id"],
        "name": r["name"],
        "short": _race_short(r),
        "date": _fmt_date(r),
        "race_type": r["race_type"],
        "num_stages": r.get("num_stages"),
        "pcs_slug": r.get("pcs_slug", ""),
        "year": r.get("year", 2026),
        "contenders": [],
    }


def _user_link(username: str) -> Markup:
    u = escape(username)
    return Markup(f'<a href="/users/{u}" class="underline hover:opacity-70">{u}</a>')


def get_season_narrative(leaderboard: list[dict], races_done: int, races_total: int) -> Markup:
    if not leaderboard:
        return Markup("La stagione non è ancora iniziata.")
    leader = leaderboard[0]
    second = leaderboard[1] if len(leaderboard) > 1 else None
    remaining = races_total - races_done
    if second is None:
        return Markup(f"{_user_link(leader['username'])} è solo in testa con {leader['total_points']} punti.")
    gap = abs(second["gap"])
    l = _user_link(leader["username"])
    s = _user_link(second["username"])
    if gap == 0:
        return Markup(f"🔥 Parità assoluta! {l} e {s} al comando — tutto si decide nelle ultime {remaining} gare.")
    elif gap <= 5:
        return Markup(f"Solo {gap} pt separano {l} da {s} — lotta aperta con {remaining} gare rimaste.")
    else:
        return Markup(f"{l} guida con {leader['total_points']} pt, {gap} di vantaggio su {s} — {remaining} gare alla fine.")


def get_season_progress(season) -> dict:
    races = _load_races(season["id"])
    today = date.today()

    completed = [r for r in races if r.get("race_date") and r["race_date"] <= str(today)]
    upcoming  = [r for r in races if not r.get("race_date") or r["race_date"] > str(today)]

    if not races:
        return {
            "pct": 0, "races_done": 0, "races_total": 0,
            "days_to_end": None, "season_end_str": "",
            "days_to_next": None, "next_race_name": None, "next_race_short": None,
            "max_pts_remaining": 0, "timeline": [],
        }

    last_date_str = max(r["race_date"] for r in races if r.get("race_date"))
    last_date = date.fromisoformat(last_date_str)
    days_to_end = max(0, (last_date - today).days)

    next_race = upcoming[0] if upcoming else None
    days_to_next = (
        (date.fromisoformat(next_race["race_date"]) - today).days
        if next_race and next_race.get("race_date") else None
    )

    max_pts_remaining = sum(
        sum(gc_points(r["name"], r.get("num_stages"), pos) for pos in range(1, 4))
        for r in upcoming if r.get("race_date", "") > str(today)
    )

    _months = ["", "gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
    season_end_str = f"{last_date.day} {_months[last_date.month]}"

    timeline = []
    for r in completed:
        timeline.append({"id": r["id"], "short": _race_short(r), "name": r["name"], "status": "done", "date": _fmt_date(r)})
    if upcoming:
        nxt = upcoming[0]
        timeline.append({"id": nxt["id"], "short": _race_short(nxt), "name": nxt["name"], "status": "next", "date": _fmt_date(nxt)})
        for r in upcoming[1:]:
            timeline.append({"id": r["id"], "short": _race_short(r), "name": r["name"], "status": "upcoming", "date": _fmt_date(r)})

    return {
        "pct": int(len(completed) / len(races) * 100) if races else 0,
        "races_done": len(completed),
        "races_total": len(races),
        "days_to_end": days_to_end,
        "season_end_str": season_end_str,
        "days_to_next": days_to_next,
        "next_race_name": next_race["name"] if next_race else None,
        "next_race_short": _race_short(next_race) if next_race else None,
        "max_pts_remaining": max_pts_remaining,
        "timeline": timeline,
    }


def get_user_detail(username: str) -> dict | None:
    season = _load_season()
    if not season:
        return None

    races = _load_races(season["id"])
    ua_rows = _load_user_athletes(season["id"])
    results = _load_results([r["id"] for r in races])
    completed, _, user_roster, athletes, race_pts = _build_internal(races, ua_rows, results)

    if username not in user_roster:
        return None

    usernames = list(user_roster.keys())
    per_race = _user_race_points_list(username, completed, user_roster, race_pts)
    total = sum(per_race)

    leaderboard = get_leaderboard()
    me = next((u for u in leaderboard if u["username"] == username), None)
    rank = me["rank"] if me else 0
    gap  = me["gap"]  if me else 0
    leader_pts = leaderboard[0]["total_points"] if leaderboard else 0

    num_users = len(user_roster)
    rank_hist = _rank_history(username, usernames, completed, user_roster, race_pts)
    race_labels = [_race_short(r) for r in completed]
    rank_chart = _rank_chart_data(rank_hist, race_labels, num_users)
    per_race_rank = _per_race_ranks(username, usernames, completed, user_roster, race_pts)

    all_pts = [
        race_pts.get(r["id"], {}).get(a, {}).get("points", 0)
        for u, aids in user_roster.items() for a in aids for r in completed
    ]
    league_avg = sum(all_pts) / len(all_pts) if all_pts else 0.0

    acq_by_aid = {ua["athlete_id"]: ua.get("acquisition_price")
                  for ua in ua_rows if ua["users"]["username"] == username}

    athlete_ids = user_roster[username]
    ath_list = []
    for aid in athlete_ids:
        ath = athletes.get(aid, {"full_name": aid, "team": "", "flag": "", "status": "active"})
        race_p = [race_pts.get(r["id"], {}).get(aid, {}).get("points", 0) for r in completed]
        ath_total = sum(race_p)

        best_pos, best_race_name = None, None
        for r in completed:
            res = race_pts.get(r["id"], {}).get(aid)
            if res:
                if best_pos is None or res["position"] < best_pos:
                    best_pos = res["position"]
                    best_race_name = _race_short(r)
        pos_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(best_pos, f"{best_pos}°" if best_pos else "—")
        best_str = f"{pos_emoji} {best_race_name}" if best_race_name else "—"

        ath_list.append({
            "id": aid,
            "full_name": ath["full_name"],
            "team": ath["team"],
            "flag": ath["flag"],
            "pcs_slug": ath.get("pcs_slug", ""),
            "slug": ath.get("slug") or _slugify(ath["full_name"]),
            "photo_url": ath.get("photo_url") or _athlete_photo_url(ath.get("pcs_slug", "")),
            "status": ath.get("status", "active"),
            "acquisition_price": acq_by_aid.get(aid),
            "best": best_str,
            "total_points": ath_total,
            "race_points": race_p,
            "vs_avg": round(ath_total - league_avg, 1),
        })
    ath_list.sort(key=lambda a: -a["total_points"])
    max_athlete_pts = max((a["total_points"] for a in ath_list), default=1) or 1

    races_detail = []
    for i, race in enumerate(completed):
        res_list = []
        for aid in athlete_ids:
            res = race_pts.get(race["id"], {}).get(aid)
            if res:
                ath_data = athletes.get(aid, {})
                res_list.append({
                    "athlete": ath_data.get("full_name", aid),
                    "slug": ath_data.get("slug") or _slugify(ath_data.get("full_name", aid)),
                    "position": res["position"],
                    "points": res["points"],
                })
        res_list.sort(key=lambda r: r["position"])
        races_detail.append({
            "id": race["id"],
            "name": race["name"],
            "short": _race_short(race),
            "date": _fmt_date(race),
            "results": res_list,
            "total": sum(r["points"] for r in res_list),
            "weekly_rank": per_race_rank[i],
        })

    cumulative, running = [], 0
    for pts in per_race:
        running += pts
        cumulative.append(running)

    max_race_pts = max(per_race) if per_race else 1
    max_race_pts = max_race_pts or 1

    races_led = sum(
        1 for i in range(len(completed))
        if _user_total_up_to(username, completed, user_roster, race_pts, i + 1)
        == max(_user_total_up_to(u, completed, user_roster, race_pts, i + 1) for u in usernames)
    )
    best_idx  = per_race.index(max(per_race)) if per_race else 0
    worst_idx = per_race.index(min(per_race)) if per_race else 0

    # Head-to-head
    opponents = [u for u in usernames if u != username]
    my_per = per_race
    h2h = []
    for j, opp in enumerate(opponents):
        opp_per = _user_race_points_list(opp, completed, user_roster, race_pts)
        wins = draws = losses = diff = 0
        for my, op in zip(my_per, opp_per):
            if my > op:   wins += 1
            elif my == op: draws += 1
            else:          losses += 1
            diff += my - op
        h2h.append({
            "username": opp,
            "initials": opp[:2].upper(),
            "color": _AVATAR_COLORS[j % len(_AVATAR_COLORS)],
            "wins": wins, "draws": draws, "losses": losses, "point_diff": diff,
        })
    h2h.sort(key=lambda x: (-x["wins"], x["losses"]))

    return {
        "rank": rank,
        "username": username,
        "initials": username[:2].upper(),
        "total_points": total,
        "gap": gap,
        "leader_points": leader_pts,
        "races_led": races_led,
        "streak": _streak(per_race),
        "best_race_name": race_labels[best_idx] if race_labels else "—",
        "best_race_pts": per_race[best_idx] if per_race else 0,
        "worst_race_name": race_labels[worst_idx] if race_labels else "—",
        "worst_race_pts": per_race[worst_idx] if per_race else 0,
        "athletes": ath_list,
        "max_athlete_pts": max_athlete_pts,
        "league_avg": round(league_avg, 1),
        "races": races_detail,
        "race_labels": race_labels,
        "race_ids": [r["id"] for r in completed],
        "race_names": [r["name"] for r in completed],
        "race_points": per_race,
        "per_race_rank": per_race_rank,
        "cumulative_points": cumulative,
        "max_race_pts": max_race_pts,
        "rank_history": rank_hist,
        "rank_chart": rank_chart,
        "num_users": num_users,
        "h2h": h2h,
        "season_name": season.get("name", "Stagione"),
    }


def get_all_races() -> list[dict]:
    season = _load_season()
    if not season:
        return []
    races = _load_races(season["id"])
    today = str(date.today())
    result = []
    for r in races:
        result.append({
            "id": r["id"],
            "name": r["name"],
            "date": _fmt_date(r),
            "race_date": r.get("race_date", ""),
            "race_type": r["race_type"],
            "pcs_slug": r.get("pcs_slug", ""),
            "year": r.get("year", 2026),
            "num_stages": r.get("num_stages"),
            "is_completed": bool(r.get("race_date")) and r["race_date"] <= today,
            "difficulty": r.get("difficulty"),
            "prestige": r.get("prestige"),
        })
    return result


def get_race_detail(race_id: str, user_id: str | None = None) -> dict | None:
    db = get_db()
    rows = db.table("races").select("*").eq("id", race_id).limit(1).execute().data
    if not rows:
        return None
    race = rows[0]

    today = str(date.today())
    is_completed = bool(race.get("race_date")) and race["race_date"] <= today

    result_rows = (
        db.table("race_results")
        .select("*")
        .eq("race_id", race_id)
        .eq("result_type", "gc")
        .eq("stage_number", 0)
        .order("position")
        .execute()
        .data
    )

    athlete_ids = [r["athlete_id"] for r in result_rows]

    athletes_map: dict[str, dict] = {}
    if athlete_ids:
        ath_rows = (
            db.table("athletes")
            .select("id,full_name,team,nationality,pcs_slug,slug,status")
            .in_("id", athlete_ids)
            .execute()
            .data
        )
        for a in ath_rows:
            athletes_map[a["id"]] = a

    season = _load_season()

    # Build athlete → owner map for all users in the season
    owner_by_athlete: dict[str, str] = {}
    user_athlete_ids: set[str] = set()
    my_username: str | None = None

    if season:
        all_ua = (
            db.table("user_athletes")
            .select("athlete_id,user_id,users(id,username)")
            .eq("season_id", season["id"])
            .execute()
            .data
        )
        _is_uuid = False
        if user_id:
            try:
                import uuid as _uuid_mod
                _uuid_mod.UUID(user_id)
                _is_uuid = True
            except ValueError:
                pass
        for ua in all_ua:
            aid = ua["athlete_id"]
            uname = ua["users"]["username"]
            owner_by_athlete[aid] = uname
            if _is_uuid and ua["users"]["id"] == user_id:
                user_athlete_ids.add(aid)
                my_username = uname

    results = []
    for rr in result_rows:
        aid = rr["athlete_id"]
        ath = athletes_map.get(aid, {})
        full_name = ath.get("full_name", "—")
        pcs_slug = ath.get("pcs_slug") or ""
        results.append({
            "position": rr["position"],
            "athlete_id": aid,
            "full_name": full_name,
            "team": ath.get("team") or "",
            "flag": _flag(ath.get("nationality")),
            "pcs_slug": pcs_slug,
            "slug": ath.get("slug") or _slugify(full_name),
            "photo_url": _athlete_photo_url(pcs_slug),
            "status": ath.get("status", "active"),
            "points": rr["points"],
            "result_status": rr.get("status", "ok"),
            "is_mine": aid in user_athlete_ids,
            "owner": owner_by_athlete.get(aid),
        })

    # Per-user score summary for users who have athletes in this race
    user_scores: dict[str, dict] = {}
    for r in results:
        if r["owner"] and r["points"] > 0:
            u = r["owner"]
            if u not in user_scores:
                user_scores[u] = {"username": u, "total": 0, "athletes": []}
            user_scores[u]["total"] += r["points"]
            user_scores[u]["athletes"].append(r)
    user_scores_list = sorted(user_scores.values(), key=lambda x: -x["total"])

    my_results = [r for r in results if r["is_mine"]]
    my_total = sum(r["points"] for r in my_results)

    return {
        "id": race["id"],
        "name": race["name"],
        "date": _fmt_date(race),
        "race_date": race.get("race_date", ""),
        "race_type": race.get("race_type", ""),
        "pcs_slug": race.get("pcs_slug", ""),
        "year": race.get("year", 2026),
        "num_stages": race.get("num_stages"),
        "difficulty": race.get("difficulty"),
        "prestige": race.get("prestige"),
        "is_completed": is_completed,
        "results": results,
        "my_results": my_results,
        "my_total": my_total,
        "my_username": my_username,
        "user_scores": user_scores_list,
    }


def get_athlete_detail(slug: str) -> dict | None:
    db = get_db()
    rows = db.table("athletes").select("*").eq("slug", slug).limit(1).execute().data
    if not rows:
        return None
    ath_row = rows[0]
    athlete_id = ath_row["id"]

    season = _load_season()
    if not season:
        pcs_slug = ath_row.get("pcs_slug") or ""
        return {
            "id": athlete_id,
            "full_name": ath_row["full_name"],
            "team": ath_row.get("team") or "",
            "nationality": ath_row.get("nationality") or "",
            "flag": _flag(ath_row.get("nationality")),
            "pcs_slug": pcs_slug,
            "slug": ath_row.get("slug") or slug,
            "photo_url": _athlete_photo_url(pcs_slug),
            "owner": None,
            "total_points": 0,
            "best": "—",
            "races": [],
            "race_labels": [],
            "race_points": [],
        }

    # Find owner in active season
    ua_rows = db.table("user_athletes") \
        .select("user_id,users(username)") \
        .eq("athlete_id", athlete_id) \
        .eq("season_id", season["id"]) \
        .limit(1).execute().data
    owner = ua_rows[0]["users"]["username"] if ua_rows else None

    races = _load_races(season["id"])
    results_rows = (
        db.table("race_results")
        .select("*")
        .eq("athlete_id", athlete_id)
        .eq("result_type", "gc")
        .eq("stage_number", 0)
        .execute()
        .data
    )
    results_by_race = {r["race_id"]: r for r in results_rows}

    today = str(date.today())
    completed = [r for r in races if r.get("race_date") and r["race_date"] <= today]

    race_pts_list = []
    races_detail = []
    best_pos, best_race_name = None, None
    for race in completed:
        res = results_by_race.get(race["id"])
        pts = res["points"] if res else 0
        pos = res["position"] if res else None
        race_pts_list.append(pts)
        if res:
            races_detail.append({
                "id": race["id"],
                "name": race["name"],
                "short": _race_short(race),
                "date": _fmt_date(race),
                "position": pos,
                "points": pts,
            })
            if best_pos is None or pos < best_pos:
                best_pos = pos
                best_race_name = _race_short(race)

    pos_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(best_pos, f"{best_pos}°" if best_pos else "—")
    best_str = f"{pos_emoji} {best_race_name}" if best_race_name else "—"

    pcs_slug = ath_row.get("pcs_slug") or ""
    return {
        "id": athlete_id,
        "full_name": ath_row["full_name"],
        "team": ath_row.get("team") or "",
        "nationality": ath_row.get("nationality") or "",
        "flag": _flag(ath_row.get("nationality")),
        "pcs_slug": pcs_slug,
        "slug": ath_row.get("slug") or slug,
        "photo_url": _athlete_photo_url(pcs_slug),
        "status": ath_row.get("status", "active"),
        "owner": owner,
        "total_points": sum(race_pts_list),
        "best": best_str,
        "races": races_detail,
        "race_labels": [_race_short(r) for r in completed],
        "race_points": race_pts_list,
        "season_name": season.get("name", "Stagione"),
    }


def get_all_users_with_rosters() -> list[dict]:
    season = _load_season()
    if not season:
        return []

    races = _load_races(season["id"])
    ua_rows = _load_user_athletes(season["id"])
    results = _load_results([r["id"] for r in races])
    completed, _, user_roster, athletes, race_pts = _build_internal(races, ua_rows, results)

    leaderboard = get_leaderboard()
    lb_by_user = {u["username"]: u for u in leaderboard}

    acq_map: dict[str, dict[str, float | None]] = {}
    for ua in ua_rows:
        uname = ua["users"]["username"]
        acq_map.setdefault(uname, {})[ua["athlete_id"]] = ua.get("acquisition_price")

    out = []
    for username, athlete_ids in user_roster.items():
        lb = lb_by_user.get(username, {})
        per_race = _user_race_points_list(username, completed, user_roster, race_pts)

        ath_list = []
        for aid in athlete_ids:
            ath = athletes.get(aid, {"full_name": aid, "team": "", "flag": "", "status": "active"})
            ath_pts = sum(
                race_pts.get(r["id"], {}).get(aid, {}).get("points", 0)
                for r in completed
            )
            ath_list.append({
                "full_name": ath["full_name"],
                "flag": ath["flag"],
                "team": ath["team"],
                "status": ath.get("status", "active"),
                "acquisition_price": acq_map.get(username, {}).get(aid),
                "total_points": ath_pts,
            })
        ath_list.sort(key=lambda a: -a["total_points"])

        out.append({
            "username": username,
            "initials": username[:2].upper(),
            "color": lb.get("color", "primary"),
            "rank": lb.get("rank", 0),
            "total_points": lb.get("total_points", 0),
            "gap": lb.get("gap", 0),
            "streak": _streak(per_race),
            "athletes": ath_list,
        })

    out.sort(key=lambda u: u["rank"])
    return out
