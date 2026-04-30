from dataclasses import dataclass
from datetime import date

from database import get_db
import utils


@dataclass
class SeasonContext:
    season: dict
    races: list[dict]
    ua_rows: list[dict]
    completed: list[dict]
    upcoming: list[dict]
    user_roster: dict[str, list[str]]
    athletes: dict[str, dict]
    race_pts: dict[str, dict[str, dict]]


def load_season_context() -> SeasonContext | None:
    season = _load_season()
    if not season:
        return None
    races = _load_races(season["id"])
    ua_rows = _load_user_athletes(season["id"])
    results = _load_results([r["id"] for r in races])
    completed, upcoming, user_roster, athletes, race_pts = _build_internal(races, ua_rows, results)
    return SeasonContext(
        season=season, races=races, ua_rows=ua_rows,
        completed=completed, upcoming=upcoming,
        user_roster=user_roster, athletes=athletes, race_pts=race_pts,
    )


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


def _build_internal(races, ua_rows, result_rows):
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
                "flag": utils.flag_emoji(ath.get("nationality")),
                "pcs_slug": pcs_slug,
                "slug": ath.get("slug") or utils.slugify(ath["full_name"]),
                "status": ath.get("status", "active"),
                "photo_url": utils.athlete_photo_url(pcs_slug),
            }

    race_pts: dict[str, dict[str, dict]] = {}
    for rr in result_rows:
        rid = rr["race_id"]
        aid = rr["athlete_id"]
        if rid not in race_pts:
            race_pts[rid] = {}
        race_pts[rid][aid] = {
            "position": rr["position"],
            "points": rr["points"],
            "status": rr.get("status", "ok"),
        }

    completed = [r for r in races if r.get("race_date") and r["race_date"] <= str(today)]
    upcoming  = [r for r in races if not r.get("race_date") or r["race_date"] > str(today)]

    return completed, upcoming, user_roster, athletes, race_pts


def _user_race_points_list(username, completed, user_roster, race_pts) -> list[int]:
    athlete_ids = user_roster.get(username, [])
    return [
        sum(race_pts.get(r["id"], {}).get(a, {}).get("points", 0) for a in athlete_ids)
        for r in completed
    ]


def _rank_history(username, usernames, completed, user_roster, race_pts) -> list[int]:
    """O(n × users) via incremental running totals — was O(n² × users)."""
    running = {u: 0 for u in usernames}
    hist = []
    for race in completed:
        for u in usernames:
            running[u] += sum(
                race_pts.get(race["id"], {}).get(a, {}).get("points", 0)
                for a in user_roster.get(u, [])
            )
        sorted_u = sorted(running, key=lambda u: (-running[u], u))
        hist.append(sorted_u.index(username) + 1)
    return hist


def _streak(per_race: list[int]) -> str:
    if len(per_race) < 2:
        return "neutral"
    last, prev = per_race[-1], per_race[-2]
    if last > prev:
        return "hot"
    if last < prev:
        return "cold"
    return "neutral"
