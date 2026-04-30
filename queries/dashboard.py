from datetime import date

from markupsafe import Markup, escape

from database import get_db
import utils
from scoring import gc_points
from .context import (
    SeasonContext,
    load_season_context,
    _user_race_points_list,
    _rank_history,
    _streak,
)


def get_leaderboard(ctx: SeasonContext | None = None) -> list[dict]:
    ctx = ctx or load_season_context()
    if not ctx or not ctx.user_roster:
        return []

    completed   = ctx.completed
    user_roster = ctx.user_roster
    race_pts    = ctx.race_pts
    usernames   = list(user_roster.keys())

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
    max_pts    = rows[0]["total"] if rows else 1
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
            "color": utils.AVATAR_COLORS[i % len(utils.AVATAR_COLORS)],
        })
    return result


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


def get_race_chart_data(ctx: SeasonContext | None = None) -> dict:
    ctx = ctx or load_season_context()
    if not ctx:
        return {"labels": [], "weekly_maxes": []}
    usernames    = list(ctx.user_roster.keys())
    labels       = utils.get_race_labels(ctx.completed)
    weekly_maxes = get_race_weekly_maxes(usernames, ctx.completed, ctx.user_roster, ctx.race_pts)
    return {"labels": labels, "weekly_maxes": weekly_maxes}


def get_recent_races(n: int = 3, ctx: SeasonContext | None = None) -> list[dict]:
    ctx = ctx or load_season_context()
    if not ctx:
        return []

    recent = list(reversed(ctx.completed))[:n]
    out = []
    for race in recent:
        scores = []
        for username, athlete_ids in ctx.user_roster.items():
            r_results = ctx.race_pts.get(race["id"], {})
            user_results = [
                {
                    "athlete": ctx.athletes[a]["full_name"],
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
                "short": utils.race_short(race),
                "date": utils.fmt_date(race),
                "race_type": race["race_type"],
                "race_date": race.get("race_date", ""),
                "pcs_slug": race.get("pcs_slug", ""),
                "year": race.get("year", 2026),
            },
            "scores": scores,
        })
    return out


def get_top_athletes(ctx: SeasonContext | None = None) -> list[dict]:
    ctx = ctx or load_season_context()
    if not ctx:
        return []

    athlete_owner: dict[str, str] = {}
    for username, aids in ctx.user_roster.items():
        for aid in aids:
            athlete_owner[aid] = username

    scores: dict[str, int] = {}
    best: dict[str, tuple] = {}
    for race in ctx.completed:
        short = utils.race_short(race)
        for aid, res in ctx.race_pts.get(race["id"], {}).items():
            scores[aid] = scores.get(aid, 0) + res["points"]
            if aid not in best or res["position"] < best[aid][0]:
                best[aid] = (res["position"], short)

    ranked = sorted(scores, key=lambda a: -scores[a])[:5]

    athletes = ctx.athletes
    missing = [aid for aid in ranked if aid not in athletes]
    if missing:
        for r in (
            get_db()
            .table("athletes")
            .select("id,full_name,team,nationality,pcs_slug,slug")
            .in_("id", missing)
            .execute()
            .data
        ):
            pcs_slug = r.get("pcs_slug") or ""
            athletes[r["id"]] = {
                "id": r["id"],
                "full_name": r["full_name"],
                "team": r.get("team") or "",
                "flag": utils.flag_emoji(r.get("nationality")),
                "pcs_slug": pcs_slug,
                "slug": r.get("slug") or utils.slugify(r["full_name"]),
                "photo_url": utils.athlete_photo_url(pcs_slug),
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
            "slug": ath.get("slug") or utils.slugify(ath["full_name"]),
            "photo_url": ath.get("photo_url") or utils.athlete_photo_url(ath.get("pcs_slug", "")),
            "total_points": scores[aid],
            "best": f"{pos_emoji} {br[1]}" if br[1] else "—",
            "owner": athlete_owner.get(aid, "—"),
        })
    return result


def get_next_race(ctx: SeasonContext | None = None) -> dict:
    ctx = ctx or load_season_context()
    if not ctx or not ctx.upcoming:
        return {}
    r = ctx.upcoming[0]
    return {
        "id": r["id"],
        "name": r["name"],
        "short": utils.race_short(r),
        "date": utils.fmt_date(r),
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
    if gap <= 5:
        return Markup(f"Solo {gap} pt separano {l} da {s} — lotta aperta con {remaining} gare rimaste.")
    return Markup(f"{l} guida con {leader['total_points']} pt, {gap} di vantaggio su {s} — {remaining} gare alla fine.")


def get_season_progress(ctx: SeasonContext | None = None) -> dict:
    _empty = {
        "pct": 0, "races_done": 0, "races_total": 0,
        "days_to_end": None, "season_end_str": "",
        "days_to_next": None, "next_race_name": None, "next_race_short": None,
        "max_pts_remaining": 0, "timeline": [],
    }
    ctx = ctx or load_season_context()
    if not ctx or not ctx.races:
        return _empty

    races     = ctx.races
    completed = ctx.completed
    upcoming  = ctx.upcoming
    today     = date.today()

    last_date_str = max(r["race_date"] for r in races if r.get("race_date"))
    last_date     = date.fromisoformat(last_date_str)
    days_to_end   = max(0, (last_date - today).days)

    next_race    = upcoming[0] if upcoming else None
    days_to_next = (
        (date.fromisoformat(next_race["race_date"]) - today).days
        if next_race and next_race.get("race_date") else None
    )

    max_pts_remaining = sum(
        sum(gc_points(r["name"], r.get("num_stages"), pos) for pos in range(1, 4))
        for r in upcoming if r.get("race_date", "") > str(today)
    )

    season_end_str = f"{last_date.day} {utils.MONTHS_IT[last_date.month]}"

    timeline = []
    for r in completed:
        timeline.append({"id": r["id"], "short": utils.race_short(r), "name": r["name"], "status": "done", "date": utils.fmt_date(r)})
    if upcoming:
        nxt = upcoming[0]
        timeline.append({"id": nxt["id"], "short": utils.race_short(nxt), "name": nxt["name"], "status": "next", "date": utils.fmt_date(nxt)})
        for r in upcoming[1:]:
            timeline.append({"id": r["id"], "short": utils.race_short(r), "name": r["name"], "status": "upcoming", "date": utils.fmt_date(r)})

    return {
        "pct": int(len(completed) / len(races) * 100),
        "races_done": len(completed),
        "races_total": len(races),
        "days_to_end": days_to_end,
        "season_end_str": season_end_str,
        "days_to_next": days_to_next,
        "next_race_name": next_race["name"] if next_race else None,
        "next_race_short": utils.race_short(next_race) if next_race else None,
        "max_pts_remaining": max_pts_remaining,
        "timeline": timeline,
    }
