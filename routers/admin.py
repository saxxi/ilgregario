import asyncio
from datetime import datetime, timezone
from urllib.parse import quote_plus

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

import auth as auth_module
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _guard(request: Request):
    session = auth_module.get_session(request)
    if not session or not session.get("is_admin"):
        return None, RedirectResponse("/login", status_code=302)
    return session, None


def _redir(path: str, msg: str = "") -> RedirectResponse:
    url = f"{path}?msg={quote_plus(msg)}" if msg else path
    return RedirectResponse(url, status_code=303)


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

@router.get("/admin", response_class=HTMLResponse)
async def admin_index(request: Request):
    session, err = _guard(request)
    if err:
        return err
    return templates.TemplateResponse(
        request, "admin/index.html", {"session": session}
    )


@router.post("/sync-races")
async def sync_races(request: Request):
    session, err = _guard(request)
    if err:
        return JSONResponse({"error": "unauthorized"}, status_code=403)
    from scripts.sync_races import sync
    summary = await asyncio.to_thread(sync)
    return JSONResponse(summary)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@router.get("/admin/users", response_class=HTMLResponse)
async def users_list(request: Request, msg: str = ""):
    session, err = _guard(request)
    if err:
        return err
    db = get_db()
    users = (
        db.table("users")
        .select("id, username, is_admin, created_at")
        .order("created_at")
        .execute()
        .data or []
    )
    return templates.TemplateResponse(
        request, "admin/users.html",
        {"session": session, "users": users, "msg": msg},
    )


@router.post("/admin/users/create")
async def users_create(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    is_admin: str = Form(default=""),
):
    session, err = _guard(request)
    if err:
        return err
    db = get_db()
    try:
        db.table("users").insert({
            "username": username.strip(),
            "password_hash": auth_module.hash_password(password),
            "is_admin": bool(is_admin),
        }).execute()
        return _redir("/admin/users", "Utente creato")
    except Exception as exc:
        return _redir("/admin/users", f"Errore: {exc}")


@router.get("/admin/users/{user_id}", response_class=HTMLResponse)
async def user_detail(request: Request, user_id: str, season_id: str = "", msg: str = ""):
    session, err = _guard(request)
    if err:
        return err
    db = get_db()
    user = db.table("users").select("id, username, is_admin").eq("id", user_id).single().execute().data
    seasons = db.table("seasons").select("id, name, year, active").order("year", desc=True).execute().data or []

    selected_season = None
    assignments = []
    assigned_ids = set()
    all_athletes = []
    taken_athletes = {}

    if seasons:
        if season_id:
            selected_season = next((s for s in seasons if s["id"] == season_id), seasons[0])
        else:
            selected_season = next((s for s in seasons if s["active"]), seasons[0])

        assignments = (
            db.table("user_athletes")
            .select("id, athlete_id, acquisition_price, athletes(full_name, team, nationality)")
            .eq("user_id", user_id)
            .eq("season_id", selected_season["id"])
            .execute()
            .data or []
        )
        assigned_ids = {a["athlete_id"] for a in assignments}
        all_athletes = (
            db.table("athletes").select("id, full_name").order("full_name").execute().data or []
        )
        all_season_assignments = (
            db.table("user_athletes")
            .select("athlete_id, user_id, users(username)")
            .eq("season_id", selected_season["id"])
            .neq("user_id", user_id)
            .execute()
            .data or []
        )
        taken_athletes = {a["athlete_id"]: a["users"]["username"] for a in all_season_assignments if a.get("users")}

    return templates.TemplateResponse(
        request, "admin/user_athletes.html",
        {
            "session": session,
            "user": user,
            "seasons": seasons,
            "selected_season": selected_season,
            "assignments": assignments,
            "assigned_ids": assigned_ids,
            "all_athletes": all_athletes,
            "taken_athletes": taken_athletes,
            "msg": msg,
        },
    )


# ---------------------------------------------------------------------------
# Seasons
# ---------------------------------------------------------------------------

@router.get("/admin/seasons", response_class=HTMLResponse)
async def seasons_list(request: Request, msg: str = ""):
    session, err = _guard(request)
    if err:
        return err
    seasons = (
        get_db().table("seasons")
        .select("id, name, year, active, created_at, total_budget, min_runners, max_runners")
        .order("year", desc=True)
        .execute()
        .data or []
    )
    return templates.TemplateResponse(
        request, "admin/seasons.html",
        {"session": session, "seasons": seasons, "msg": msg},
    )


@router.post("/admin/seasons/create")
async def seasons_create(
    request: Request,
    year: str = Form(...),
    total_budget: str = Form(default="500"),
    min_runners: str = Form(default="9"),
    max_runners: str = Form(default="30"),
):
    session, err = _guard(request)
    if err:
        return err
    try:
        get_db().table("seasons").insert({
            "name": str(int(year)),
            "year": int(year),
            "total_budget": int(total_budget) if total_budget.strip() else 500,
            "min_runners": int(min_runners) if min_runners.strip() else 9,
            "max_runners": int(max_runners) if max_runners.strip() else 30,
        }).execute()
        return _redir("/admin/seasons", "Stagione creata")
    except Exception as exc:
        return _redir("/admin/seasons", f"Errore: {exc}")


@router.post("/admin/seasons/{season_id}/edit")
async def seasons_edit(
    request: Request,
    season_id: str,
    total_budget: str = Form(default="500"),
    min_runners: str = Form(default="9"),
    max_runners: str = Form(default="30"),
):
    session, err = _guard(request)
    if err:
        return err
    try:
        get_db().table("seasons").update({
            "total_budget": int(total_budget) if total_budget.strip() else 500,
            "min_runners": int(min_runners) if min_runners.strip() else 9,
            "max_runners": int(max_runners) if max_runners.strip() else 30,
        }).eq("id", season_id).execute()
        return _redir("/admin/seasons", "Stagione aggiornata")
    except Exception as exc:
        return _redir("/admin/seasons", f"Errore: {exc}")


@router.post("/admin/seasons/{season_id}/activate")
async def seasons_activate(request: Request, season_id: str):
    session, err = _guard(request)
    if err:
        return err
    db = get_db()
    db.table("seasons").update({"active": False}).neq("id", season_id).execute()
    db.table("seasons").update({"active": True}).eq("id", season_id).execute()
    return _redir("/admin/seasons", "Stagione attivata")


@router.post("/admin/seasons/{season_id}/delete")
async def seasons_delete(request: Request, season_id: str):
    session, err = _guard(request)
    if err:
        return err
    get_db().table("seasons").delete().eq("id", season_id).execute()
    return _redir("/admin/seasons", "Stagione eliminata")


@router.post("/admin/users/{user_id}/athletes/add")
async def user_athletes_add(
    request: Request,
    user_id: str,
    athlete_id: str = Form(...),
    season_id: str = Form(...),
    acquisition_price: str = Form(default=""),
):
    session, err = _guard(request)
    if err:
        return err
    db = get_db()
    existing = (
        db.table("user_athletes")
        .select("user_id, users(username)")
        .eq("athlete_id", athlete_id)
        .eq("season_id", season_id)
        .neq("user_id", user_id)
        .limit(1)
        .execute()
        .data or []
    )
    if existing:
        owner = (existing[0].get("users") or {}).get("username", "altro utente")
        return _redir(f"/admin/users/{user_id}?season_id={season_id}", f"Atleta già assegnato a {owner}")
    try:
        db.table("user_athletes").insert({
            "user_id": user_id,
            "athlete_id": athlete_id,
            "season_id": season_id,
            "acquisition_price": float(acquisition_price) if acquisition_price.strip() else None,
        }).execute()
        return _redir(f"/admin/users/{user_id}?season_id={season_id}", "Atleta aggiunto")
    except Exception as exc:
        return _redir(f"/admin/users/{user_id}?season_id={season_id}", f"Errore: {exc}")


@router.post("/admin/users/{user_id}/athletes/{ua_id}/delete")
async def user_athletes_delete(request: Request, user_id: str, ua_id: str, season_id: str = Form(default="")):
    session, err = _guard(request)
    if err:
        return err
    get_db().table("user_athletes").delete().eq("id", ua_id).execute()
    dest = f"/admin/users/{user_id}" + (f"?season_id={season_id}" if season_id else "")
    return _redir(dest, "Atleta rimosso")


@router.post("/admin/users/{user_id}/athletes/{ua_id}/edit-price")
async def user_athletes_edit_price(
    request: Request,
    user_id: str,
    ua_id: str,
    acquisition_price: str = Form(default=""),
    season_id: str = Form(default=""),
):
    session, err = _guard(request)
    if err:
        return err
    price = float(acquisition_price) if acquisition_price.strip() else None
    get_db().table("user_athletes").update({"acquisition_price": price}).eq("id", ua_id).execute()
    dest = f"/admin/users/{user_id}" + (f"?season_id={season_id}" if season_id else "")
    return _redir(dest, "Prezzo aggiornato")


@router.post("/admin/users/{user_id}/edit")
async def users_edit(
    request: Request,
    user_id: str,
    username: str = Form(...),
    password: str = Form(default=""),
    is_admin: str = Form(default=""),
):
    session, err = _guard(request)
    if err:
        return err
    updates = {"username": username.strip(), "is_admin": bool(is_admin)}
    if password.strip():
        updates["password_hash"] = auth_module.hash_password(password.strip())
    try:
        get_db().table("users").update(updates).eq("id", user_id).execute()
        return _redir("/admin/users", "Utente aggiornato")
    except Exception as exc:
        return _redir("/admin/users", f"Errore: {exc}")


@router.post("/admin/users/{user_id}/delete")
async def users_delete(request: Request, user_id: str):
    session, err = _guard(request)
    if err:
        return err
    get_db().table("users").delete().eq("id", user_id).execute()
    return _redir("/admin/users", "Utente eliminato")


# ---------------------------------------------------------------------------
# Athletes
# ---------------------------------------------------------------------------

@router.get("/admin/athletes/fc-fetch")
async def athletes_fc_fetch(url: str = ""):
    import asyncio
    from urllib.parse import urlparse, parse_qs
    from importers.pcs import PCSImporter

    if not url:
        return JSONResponse({"error": "URL mancante"}, status_code=400)
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""

        # ProcyclingStats URL: procyclingstats.com/rider/<slug>
        if "procyclingstats.com" in host:
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) < 2 or parts[0] != "rider":
                return JSONResponse({"error": "URL PCS non valido: formato atteso procyclingstats.com/rider/<slug>"}, status_code=400)
            slug = parts[1]
            profile = await asyncio.to_thread(PCSImporter().fetch_rider, slug)
            return JSONResponse({
                "full_name": profile.full_name,
                "nationality": profile.nationality,
                "team": profile.team,
                "pcs_slug": profile.slug,
                "firstcycling_id": None,
            })

        # FirstCycling URL: firstcycling.com/rider.php?r=<id>
        if "firstcycling.com" in host:
            params = parse_qs(parsed.query)
            if "r" not in params:
                return JSONResponse({"error": "URL FirstCycling non valido: parametro r mancante"}, status_code=400)
            rider_id = int(params["r"][0])
            return JSONResponse({
                "full_name": "",
                "nationality": "",
                "team": "",
                "pcs_slug": "",
                "firstcycling_id": rider_id,
                "warning": "FirstCycling è protetto da Cloudflare — solo l'ID è stato estratto. Usa un URL ProcyclingStats per i dati completi.",
            })

        return JSONResponse({"error": "URL non riconosciuto. Usa procyclingstats.com o firstcycling.com"}, status_code=400)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


@router.get("/admin/athletes", response_class=HTMLResponse)
async def athletes_list(request: Request, msg: str = "", q: str = ""):
    session, err = _guard(request)
    if err:
        return err
    db = get_db()
    query = db.table("athletes").select(
        "id, full_name, nationality, team, pcs_slug, last_synced_at, status"
    )
    if q:
        query = query.ilike("full_name", f"%{q}%")
    athletes = query.order("full_name").limit(200).execute().data or []
    return templates.TemplateResponse(
        request, "admin/athletes.html",
        {"session": session, "athletes": athletes, "msg": msg, "q": q},
    )


@router.post("/admin/athletes/create")
async def athletes_create(
    request: Request,
    full_name: str = Form(...),
    pcs_slug: str = Form(default=""),
    nationality: str = Form(default=""),
    team: str = Form(default=""),
    firstcycling_id: str = Form(default=""),
    status: str = Form(default="active"),
):
    session, err = _guard(request)
    if err:
        return err
    db = get_db()
    try:
        db.table("athletes").insert({
            "full_name": full_name.strip(),
            "pcs_slug": pcs_slug.strip() or None,
            "nationality": nationality.strip() or None,
            "team": team.strip() or None,
            "firstcycling_id": int(firstcycling_id) if firstcycling_id.strip() else None,
            "status": status,
        }).execute()
        return _redir("/admin/athletes", "Atleta aggiunto")
    except Exception as exc:
        return _redir("/admin/athletes", f"Errore: {exc}")


@router.post("/admin/athletes/{athlete_id}/edit")
async def athletes_edit(
    request: Request,
    athlete_id: str,
    full_name: str = Form(...),
    pcs_slug: str = Form(default=""),
    nationality: str = Form(default=""),
    team: str = Form(default=""),
    status: str = Form(default="active"),
):
    session, err = _guard(request)
    if err:
        return err
    get_db().table("athletes").update({
        "full_name": full_name.strip(),
        "pcs_slug": pcs_slug.strip() or None,
        "nationality": nationality.strip() or None,
        "team": team.strip() or None,
        "status": status,
    }).eq("id", athlete_id).execute()
    return _redir("/admin/athletes", "Atleta aggiornato")


@router.post("/admin/athletes/{athlete_id}/delete")
async def athletes_delete(request: Request, athlete_id: str):
    session, err = _guard(request)
    if err:
        return err
    get_db().table("athletes").delete().eq("id", athlete_id).execute()
    return _redir("/admin/athletes", "Atleta eliminato")


# ---------------------------------------------------------------------------
# Races
# ---------------------------------------------------------------------------

@router.get("/admin/races", response_class=HTMLResponse)
async def races_list(request: Request, msg: str = ""):
    session, err = _guard(request)
    if err:
        return err
    races = (
        get_db()
        .table("races")
        .select("id, name, year, race_type, race_date, num_stages, pcs_slug, synced_at, difficulty, prestige")
        .order("race_date", desc=True)
        .limit(200)
        .execute()
        .data or []
    )
    return templates.TemplateResponse(
        request, "admin/races.html",
        {"session": session, "races": races, "msg": msg},
    )


@router.post("/admin/races/create")
async def races_create(
    request: Request,
    name: str = Form(...),
    year: str = Form(...),
    race_type: str = Form(...),
    race_date: str = Form(default=""),
    num_stages: str = Form(default=""),
    pcs_slug: str = Form(default=""),
    difficulty: str = Form(default=""),
    prestige: str = Form(default=""),
):
    session, err = _guard(request)
    if err:
        return err
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    try:
        db.table("races").insert({
            "name": name.strip(),
            "year": int(year),
            "race_type": race_type,
            "race_date": race_date or None,
            "num_stages": int(num_stages) if num_stages else None,
            "pcs_slug": pcs_slug.strip() or None,
            "difficulty": int(difficulty) if difficulty.strip() else None,
            "prestige": int(prestige) if prestige.strip() else None,
            "difficulty_updated_at": now if difficulty.strip() else None,
            "prestige_updated_at": now if prestige.strip() else None,
        }).execute()
        return _redir("/admin/races", "Gara aggiunta")
    except Exception as exc:
        return _redir("/admin/races", f"Errore: {exc}")


@router.post("/admin/races/{race_id}/edit")
async def races_edit(
    request: Request,
    race_id: str,
    name: str = Form(...),
    year: str = Form(...),
    race_type: str = Form(...),
    race_date: str = Form(default=""),
    num_stages: str = Form(default=""),
    pcs_slug: str = Form(default=""),
    difficulty: str = Form(default=""),
    prestige: str = Form(default=""),
):
    session, err = _guard(request)
    if err:
        return err
    now = datetime.now(timezone.utc).isoformat()
    try:
        get_db().table("races").update({
            "name": name.strip(),
            "year": int(year),
            "race_type": race_type,
            "race_date": race_date or None,
            "num_stages": int(num_stages) if num_stages else None,
            "pcs_slug": pcs_slug.strip() or None,
            "difficulty": int(difficulty) if difficulty.strip() else None,
            "prestige": int(prestige) if prestige.strip() else None,
            "difficulty_updated_at": now if difficulty.strip() else None,
            "prestige_updated_at": now if prestige.strip() else None,
        }).eq("id", race_id).execute()
        return _redir("/admin/races", "Gara aggiornata")
    except Exception as exc:
        return _redir("/admin/races", f"Errore: {exc}")


@router.post("/admin/races/{race_id}/delete")
async def races_delete(request: Request, race_id: str):
    session, err = _guard(request)
    if err:
        return err
    get_db().table("races").delete().eq("id", race_id).execute()
    return _redir("/admin/races", "Gara eliminata")


# ---------------------------------------------------------------------------
# Race results
# ---------------------------------------------------------------------------

@router.get("/admin/races/{race_id}/results", response_class=HTMLResponse)
async def race_results_list(request: Request, race_id: str, msg: str = ""):
    session, err = _guard(request)
    if err:
        return err
    db = get_db()
    race = db.table("races").select("*").eq("id", race_id).single().execute().data
    results = (
        db.table("race_results")
        .select("id, position, points, result_type, stage_number, athlete_id, status, time")
        .eq("race_id", race_id)
        .order("result_type")
        .order("position")
        .execute()
        .data or []
    )
    athlete_ids = list({r["athlete_id"] for r in results})
    athlete_map = {}
    if athlete_ids:
        rows = (
            db.table("athletes")
            .select("id, full_name")
            .in_("id", athlete_ids)
            .execute()
            .data or []
        )
        athlete_map = {a["id"]: a for a in rows}
    all_athletes = (
        db.table("athletes")
        .select("id, full_name")
        .order("full_name")
        .execute()
        .data or []
    )
    return templates.TemplateResponse(
        request, "admin/race_results.html",
        {
            "session": session,
            "race": race,
            "results": results,
            "athlete_map": athlete_map,
            "all_athletes": all_athletes,
            "msg": msg,
        },
    )


@router.post("/admin/races/{race_id}/results/add")
async def race_results_add(
    request: Request,
    race_id: str,
    athlete_id: str = Form(...),
    position: str = Form(default=""),
    result_type: str = Form(...),
    stage_number: str = Form(default=""),
    time: str = Form(default=""),
    points: str = Form(default=""),
    status: str = Form(default="ok"),
):
    session, err = _guard(request)
    if err:
        return err
    from scoring import score_result
    db = get_db()
    race = db.table("races").select("name, num_stages").eq("id", race_id).single().execute().data
    sn = int(stage_number) if stage_number.strip() else 0
    pos = int(position) if position.strip() else None
    pts = int(points) if points.strip() else score_result(result_type, race["name"], race["num_stages"], pos, status)
    try:
        db.table("race_results").insert({
            "race_id": race_id,
            "athlete_id": athlete_id,
            "position": pos,
            "result_type": result_type,
            "stage_number": sn,
            "time": time.strip() or None,
            "points": pts,
            "status": status,
        }).execute()
        return _redir(f"/admin/races/{race_id}/results", "Risultato aggiunto")
    except Exception as exc:
        return _redir(f"/admin/races/{race_id}/results", f"Errore: {exc}")



@router.post("/admin/races/{race_id}/results/{result_id}/delete")
async def race_results_delete(request: Request, race_id: str, result_id: str):
    session, err = _guard(request)
    if err:
        return err
    get_db().table("race_results").delete().eq("id", result_id).execute()
    return _redir(f"/admin/races/{race_id}/results", "Risultato eliminato")
