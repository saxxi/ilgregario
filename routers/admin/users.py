import logging

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

import auth as auth_module
from database import get_db
from .shared import _guard, _guard_post, _redir, templates

router = APIRouter()
logger = logging.getLogger(__name__)

_ASSIGNABLE_ROLES = ("user", "admin")


@router.get("/admin/users", response_class=HTMLResponse)
async def users_list(request: Request, msg: str = ""):
    session, err = _guard(request)
    if err:
        return err
    db = get_db()
    users = (
        db.table("users")
        .select("id, username, role, is_admin, created_at")
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
    role: str = Form(default="user"),
):
    session, err = await _guard_post(request)
    if err:
        return err
    if role not in _ASSIGNABLE_ROLES:
        return _redir("/admin/users", "Ruolo non valido")
    db = get_db()
    try:
        db.table("users").insert({
            "username": username.strip(),
            "password_hash": auth_module.hash_password(password),
            "role": role,
            "is_admin": role == "admin",
        }).execute()
        return _redir("/admin/users", "Utente creato")
    except Exception:
        logger.exception("users_create failed")
        return _redir("/admin/users", "Errore interno")


@router.get("/admin/users/{user_id}", response_class=HTMLResponse)
async def user_detail(request: Request, user_id: str, season_id: str = "", msg: str = ""):
    session, err = _guard(request)
    if err:
        return err
    db = get_db()
    user = db.table("users").select("id, username, role, is_admin").eq("id", user_id).single().execute().data
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


@router.post("/admin/users/{user_id}/edit")
async def users_edit(
    request: Request,
    user_id: str,
    username: str = Form(...),
    password: str = Form(default=""),
    role: str = Form(default="user"),
):
    session, err = await _guard_post(request)
    if err:
        return err
    if role not in _ASSIGNABLE_ROLES:
        return _redir("/admin/users", "Ruolo non valido")
    updates = {
        "username": username.strip(),
        "role": role,
        "is_admin": role == "admin",
    }
    if password.strip():
        updates["password_hash"] = auth_module.hash_password(password.strip())
    try:
        get_db().table("users").update(updates).eq("id", user_id).execute()
        return _redir("/admin/users", "Utente aggiornato")
    except Exception:
        logger.exception("users_edit failed")
        return _redir("/admin/users", "Errore interno")


@router.post("/admin/users/{user_id}/delete")
async def users_delete(request: Request, user_id: str):
    session, err = await _guard_post(request)
    if err:
        return err
    get_db().table("users").delete().eq("id", user_id).execute()
    return _redir("/admin/users", "Utente eliminato")


@router.post("/admin/users/{user_id}/athletes/add")
async def user_athletes_add(
    request: Request,
    user_id: str,
    athlete_id: str = Form(...),
    season_id: str = Form(...),
    acquisition_price: str = Form(default=""),
):
    session, err = await _guard_post(request)
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
    except Exception:
        logger.exception("user_athletes_add failed")
        return _redir(f"/admin/users/{user_id}?season_id={season_id}", "Errore interno")


@router.post("/admin/users/{user_id}/athletes/{ua_id}/delete")
async def user_athletes_delete(request: Request, user_id: str, ua_id: str, season_id: str = Form(default="")):
    session, err = await _guard_post(request)
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
    session, err = await _guard_post(request)
    if err:
        return err
    price = float(acquisition_price) if acquisition_price.strip() else None
    get_db().table("user_athletes").update({"acquisition_price": price}).eq("id", ua_id).execute()
    dest = f"/admin/users/{user_id}" + (f"?season_id={season_id}" if season_id else "")
    return _redir(dest, "Prezzo aggiornato")
