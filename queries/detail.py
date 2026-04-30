import uuid
from datetime import date

from database import get_db
import utils
from .context import (
    SeasonContext,
    load_season_context,
    _load_season,
    _load_races,
    _user_race_points_list,
    _rank_history,
    _streak,
)
from .dashboard import get_leaderboard


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
            "x": x_for(i), "y": y_for(r), "rank": r,
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


def get_user_detail(username: str, ctx: SeasonContext | None = None) -> dict | None:
    ctx = ctx or load_season_context()
    if not ctx or username not in ctx.user_roster:
        return None

    completed   = ctx.completed
    user_roster = ctx.user_roster
    athletes    = ctx.athletes
    race_pts    = ctx.race_pts
    ua_rows     = ctx.ua_rows

    usernames = list(user_roster.keys())
    per_race  = _user_race_points_list(username, completed, user_roster, race_pts)
    total     = sum(per_race)

    leaderboard = get_leaderboard(ctx)
    me          = next((u for u in leaderboard if u["username"] == username), None)
    rank        = me["rank"] if me else 0
    gap         = me["gap"]  if me else 0
    leader_pts  = leaderboard[0]["total_points"] if leaderboard else 0

    num_users    = len(user_roster)
    rank_hist    = _rank_history(username, usernames, completed, user_roster, race_pts)
    race_labels  = utils.get_race_labels(completed)
    rank_chart   = _rank_chart_data(rank_hist, race_labels, num_users)
    per_race_rank = _per_race_ranks(username, usernames, completed, user_roster, race_pts)

    all_pts = [
        race_pts.get(r["id"], {}).get(a, {}).get("points", 0)
        for u, aids in user_roster.items() for a in aids for r in completed
    ]
    league_avg = sum(all_pts) / len(all_pts) if all_pts else 0.0

    acq_by_aid = {
        ua["athlete_id"]: ua.get("acquisition_price")
        for ua in ua_rows if ua["users"]["username"] == username
    }

    athlete_ids = user_roster[username]
    ath_list = []
    for aid in athlete_ids:
        ath      = athletes.get(aid, {"full_name": aid, "team": "", "flag": "", "status": "active"})
        race_p   = [race_pts.get(r["id"], {}).get(aid, {}).get("points", 0) for r in completed]
        ath_total = sum(race_p)

        best_pos, best_race_name = None, None
        for r in completed:
            res = race_pts.get(r["id"], {}).get(aid)
            if res and (best_pos is None or res["position"] < best_pos):
                best_pos = res["position"]
                best_race_name = utils.race_short(r)
        pos_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(best_pos, f"{best_pos}°" if best_pos else "—")
        best_str  = f"{pos_emoji} {best_race_name}" if best_race_name else "—"

        ath_list.append({
            "id": aid,
            "full_name": ath["full_name"],
            "team": ath["team"],
            "flag": ath["flag"],
            "pcs_slug": ath.get("pcs_slug", ""),
            "slug": ath.get("slug") or utils.slugify(ath["full_name"]),
            "photo_url": ath.get("photo_url") or utils.athlete_photo_url(ath.get("pcs_slug", "")),
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
                    "slug": ath_data.get("slug") or utils.slugify(ath_data.get("full_name", aid)),
                    "position": res["position"],
                    "points": res["points"],
                })
        res_list.sort(key=lambda r: r["position"])
        races_detail.append({
            "id": race["id"],
            "name": race["name"],
            "short": utils.race_short(race),
            "date": utils.fmt_date(race),
            "results": res_list,
            "total": sum(r["points"] for r in res_list),
            "weekly_rank": per_race_rank[i],
        })

    cumulative, running = [], 0
    for pts in per_race:
        running += pts
        cumulative.append(running)

    max_race_pts = max(per_race, default=1) or 1
    races_led    = sum(1 for r in rank_hist if r == 1)
    best_idx     = per_race.index(max(per_race)) if per_race else 0
    worst_idx    = per_race.index(min(per_race)) if per_race else 0

    h2h = []
    for j, opp in enumerate(u for u in usernames if u != username):
        opp_per = _user_race_points_list(opp, completed, user_roster, race_pts)
        wins = draws = losses = diff = 0
        for my, op in zip(per_race, opp_per):
            if my > op:    wins += 1
            elif my == op: draws += 1
            else:          losses += 1
            diff += my - op
        h2h.append({
            "username": opp,
            "initials": opp[:2].upper(),
            "color": utils.AVATAR_COLORS[j % len(utils.AVATAR_COLORS)],
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
        "season_name": ctx.season.get("name", "Stagione"),
    }


def get_all_races(ctx: SeasonContext | None = None) -> list[dict]:
    ctx = ctx or load_season_context()
    if not ctx:
        return []
    today = str(date.today())
    return [
        {
            "id": r["id"],
            "name": r["name"],
            "date": utils.fmt_date(r),
            "race_date": r.get("race_date", ""),
            "race_type": r["race_type"],
            "pcs_slug": r.get("pcs_slug", ""),
            "year": r.get("year", 2026),
            "num_stages": r.get("num_stages"),
            "is_completed": bool(r.get("race_date")) and r["race_date"] <= today,
            "difficulty": r.get("difficulty"),
            "prestige": r.get("prestige"),
        }
        for r in ctx.races
    ]


def get_race_detail(race_id: str, user_id: str | None = None) -> dict | None:
    db = get_db()
    rows = db.table("races").select("*").eq("id", race_id).limit(1).execute().data
    if not rows:
        return None
    race = rows[0]

    today        = str(date.today())
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

    athletes_map: dict[str, dict] = {}
    athlete_ids_in_results = [r["athlete_id"] for r in result_rows]
    if athlete_ids_in_results:
        for a in (
            db.table("athletes")
            .select("id,full_name,team,nationality,pcs_slug,slug,status")
            .in_("id", athlete_ids_in_results)
            .execute()
            .data
        ):
            athletes_map[a["id"]] = a

    season               = _load_season()
    owner_by_athlete: dict[str, str] = {}
    user_athlete_ids: set[str]       = set()
    my_username: str | None          = None

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
                uuid.UUID(user_id)
                _is_uuid = True
            except ValueError:
                pass
        for ua in all_ua:
            aid   = ua["athlete_id"]
            uname = ua["users"]["username"]
            owner_by_athlete[aid] = uname
            if _is_uuid and ua["users"]["id"] == user_id:
                user_athlete_ids.add(aid)
                my_username = uname

    results = []
    for rr in result_rows:
        aid       = rr["athlete_id"]
        ath       = athletes_map.get(aid, {})
        full_name = ath.get("full_name", "—")
        pcs_slug  = ath.get("pcs_slug") or ""
        results.append({
            "position": rr["position"],
            "athlete_id": aid,
            "full_name": full_name,
            "team": ath.get("team") or "",
            "flag": utils.flag_emoji(ath.get("nationality")),
            "pcs_slug": pcs_slug,
            "slug": ath.get("slug") or utils.slugify(full_name),
            "photo_url": utils.athlete_photo_url(pcs_slug),
            "status": ath.get("status", "active"),
            "points": rr["points"],
            "result_status": rr.get("status", "ok"),
            "is_mine": aid in user_athlete_ids,
            "owner": owner_by_athlete.get(aid),
        })

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
    my_total   = sum(r["points"] for r in my_results)

    return {
        "id": race["id"],
        "name": race["name"],
        "date": utils.fmt_date(race),
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
    ath_row    = rows[0]
    athlete_id = ath_row["id"]
    pcs_slug   = ath_row.get("pcs_slug") or ""

    season = _load_season()
    if not season:
        return {
            "id": athlete_id,
            "full_name": ath_row["full_name"],
            "team": ath_row.get("team") or "",
            "nationality": ath_row.get("nationality") or "",
            "flag": utils.flag_emoji(ath_row.get("nationality")),
            "pcs_slug": pcs_slug,
            "slug": ath_row.get("slug") or slug,
            "photo_url": utils.athlete_photo_url(pcs_slug),
            "owner": None,
            "total_points": 0,
            "best": "—",
            "races": [],
            "race_labels": [],
            "race_points": [],
        }

    ua_rows = (
        db.table("user_athletes")
        .select("user_id,users(username)")
        .eq("athlete_id", athlete_id)
        .eq("season_id", season["id"])
        .limit(1).execute().data
    )
    owner = ua_rows[0]["users"]["username"] if ua_rows else None

    races        = _load_races(season["id"])
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

    today     = str(date.today())
    completed = [r for r in races if r.get("race_date") and r["race_date"] <= today]

    race_pts_list: list[int] = []
    races_detail:  list[dict] = []
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
                "short": utils.race_short(race),
                "date": utils.fmt_date(race),
                "position": pos,
                "points": pts,
            })
            if best_pos is None or pos < best_pos:
                best_pos = pos
                best_race_name = utils.race_short(race)

    pos_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(best_pos, f"{best_pos}°" if best_pos else "—")
    best_str  = f"{pos_emoji} {best_race_name}" if best_race_name else "—"

    return {
        "id": athlete_id,
        "full_name": ath_row["full_name"],
        "team": ath_row.get("team") or "",
        "nationality": ath_row.get("nationality") or "",
        "flag": utils.flag_emoji(ath_row.get("nationality")),
        "pcs_slug": pcs_slug,
        "slug": ath_row.get("slug") or slug,
        "photo_url": utils.athlete_photo_url(pcs_slug),
        "status": ath_row.get("status", "active"),
        "owner": owner,
        "total_points": sum(race_pts_list),
        "best": best_str,
        "races": races_detail,
        "race_labels": [utils.race_short(r) for r in completed],
        "race_points": race_pts_list,
        "season_name": season.get("name", "Stagione"),
    }


def get_all_users_with_rosters(ctx: SeasonContext | None = None) -> list[dict]:
    ctx = ctx or load_season_context()
    if not ctx:
        return []

    leaderboard = get_leaderboard(ctx)
    lb_by_user  = {u["username"]: u for u in leaderboard}

    acq_map: dict[str, dict[str, float | None]] = {}
    for ua in ctx.ua_rows:
        uname = ua["users"]["username"]
        acq_map.setdefault(uname, {})[ua["athlete_id"]] = ua.get("acquisition_price")

    out = []
    for username, athlete_ids in ctx.user_roster.items():
        lb       = lb_by_user.get(username, {})
        per_race = _user_race_points_list(username, ctx.completed, ctx.user_roster, ctx.race_pts)

        ath_list = []
        for aid in athlete_ids:
            ath     = ctx.athletes.get(aid, {"full_name": aid, "team": "", "flag": "", "status": "active"})
            ath_pts = sum(
                ctx.race_pts.get(r["id"], {}).get(aid, {}).get("points", 0)
                for r in ctx.completed
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
