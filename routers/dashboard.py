import uuid

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import auth as auth_module
import queries as db_queries
from database import get_db
from templates_env import templates

router = APIRouter()


def _catchability(leaderboard: list[dict], max_pts_remaining: int) -> list[dict]:
    if not leaderboard:
        return []
    leader_pts = leaderboard[0]["total_points"]
    result = []
    for entry in leaderboard[1:]:
        gap = entry["total_points"] - leader_pts  # negative
        can_catch = entry["total_points"] + max_pts_remaining > leader_pts
        result.append({
            "username": entry["username"],
            "gap": gap,
            "can_catch": can_catch,
            "rank": entry["rank"],
        })
    return result


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    session = auth_module.get_session(request)

    ctx = db_queries.load_season_context()

    leaderboard     = db_queries.get_leaderboard(ctx)
    recent_races    = db_queries.get_recent_races(3, ctx)
    top_athletes    = db_queries.get_top_athletes(ctx)
    next_race       = db_queries.get_next_race(ctx)
    race_chart      = db_queries.get_race_chart_data(ctx)
    season_progress = db_queries.get_season_progress(ctx)

    races_done  = season_progress.get("races_done", 0)
    races_total = season_progress.get("races_total", 0)
    season_name = ctx.season.get("name", "Stagione") if ctx else "Stagione"

    podium       = leaderboard[:3] if len(leaderboard) >= 3 else leaderboard
    narrative    = db_queries.get_season_narrative(leaderboard, races_done, races_total)
    max_pts      = season_progress.get("max_pts_remaining", 0)
    catchability = _catchability(leaderboard, max_pts)

    return templates.TemplateResponse(
        request,
        "dashboard/index.html",
        {
            "session": session,
            "leaderboard": leaderboard,
            "podium": podium,
            "recent_races": recent_races,
            "season_name": season_name,
            "races_done": races_done,
            "races_total": races_total,
            "season_narrative": narrative,
            "race_labels": race_chart["labels"],
            "race_weekly_maxes": race_chart["weekly_maxes"],
            "top_athletes": top_athletes,
            "next_race": next_race,
            "season_progress": season_progress,
            "catchability": catchability,
        },
    )


@router.get("/users", response_class=HTMLResponse)
async def users_list(request: Request):
    session = auth_module.get_session(request)
    users = db_queries.get_all_users_with_rosters()
    return templates.TemplateResponse(
        request,
        "dashboard/users.html",
        {"session": session, "users": users},
    )


@router.get("/users/{username}", response_class=HTMLResponse)
async def user_detail(request: Request, username: str):
    session = auth_module.get_session(request)
    detail = db_queries.get_user_detail(username)
    if detail is None:
        return HTMLResponse("Utente non trovato", status_code=404)
    return templates.TemplateResponse(
        request,
        "dashboard/user.html",
        {"session": session, "user": detail},
    )


@router.get("/account", response_class=HTMLResponse)
async def account_page(request: Request):
    session = auth_module.get_session(request)
    if not session or session.get("is_admin"):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(
        request, "dashboard/account.html",
        {"session": session, "error": None, "success": None},
    )


@router.post("/account", response_class=HTMLResponse)
async def account_update(
    request: Request,
    username: str = Form(...),
    current_password: str = Form(...),
    new_password: str = Form(""),
    confirm_password: str = Form(""),
    csrf_token: str = Form(default=""),
):
    session = auth_module.get_session(request)
    if not session or session.get("is_admin"):
        return RedirectResponse("/dashboard", status_code=302)
    if not auth_module.verify_csrf_token(csrf_token, session["user_id"]):
        return HTMLResponse("CSRF token non valido", status_code=403)

    db      = get_db()
    user_id = session["user_id"]
    user    = db.table("users").select("*").eq("id", user_id).single().execute().data

    def render(error=None, success=None):
        return templates.TemplateResponse(
            request, "dashboard/account.html",
            {"session": session, "error": error, "success": success},
        )

    if not auth_module.verify_password(current_password, user["password_hash"]):
        return render(error="Password attuale non corretta.")

    username = username.strip()
    if not username:
        return render(error="Il nome utente non può essere vuoto.")

    updates = {}

    if username != user["username"]:
        taken = db.table("users").select("id").eq("username", username).execute().data
        if taken:
            return render(error="Nome utente già in uso.")
        updates["username"] = username

    if new_password:
        if new_password != confirm_password:
            return render(error="Le nuove password non coincidono.")
        updates["password_hash"] = auth_module.hash_password(new_password)

    if updates:
        db.table("users").update(updates).eq("id", user_id).execute()

    new_username = updates.get("username", user["username"])
    new_token    = auth_module.create_session_token(user_id, role=session.get("role", "user"), username=new_username)
    response = templates.TemplateResponse(
        request, "dashboard/account.html",
        {"session": {**session, "username": new_username}, "error": None, "success": "Profilo aggiornato."},
    )
    response.set_cookie(auth_module.SESSION_COOKIE, new_token, max_age=auth_module.MAX_AGE, httponly=True)
    return response


@router.get("/athletes/{slug}", response_class=HTMLResponse)
async def athlete_detail(request: Request, slug: str):
    session = auth_module.get_session(request)
    detail  = db_queries.get_athlete_detail(slug)
    if detail is None:
        return HTMLResponse("Atleta non trovato", status_code=404)
    return templates.TemplateResponse(
        request,
        "dashboard/athlete.html",
        {"session": session, "athlete": detail},
    )


@router.get("/races", response_class=HTMLResponse)
async def races_list(request: Request):
    session = auth_module.get_session(request)
    races   = db_queries.get_all_races()
    return templates.TemplateResponse(
        request,
        "dashboard/races.html",
        {"session": session, "races": races},
    )


@router.get("/races/{race_id}", response_class=HTMLResponse)
async def race_detail(request: Request, race_id: str):
    try:
        uuid.UUID(race_id)
    except ValueError:
        return HTMLResponse("Gara non trovata", status_code=404)
    session = auth_module.get_session(request)
    user_id = session["user_id"] if session else None
    detail  = db_queries.get_race_detail(race_id, user_id=user_id)
    if detail is None:
        return HTMLResponse("Gara non trovata", status_code=404)
    return templates.TemplateResponse(
        request,
        "dashboard/race.html",
        {"session": session, "race": detail},
    )
