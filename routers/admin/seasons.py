from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from database import get_db
from .shared import _guard, _redir, templates

router = APIRouter()


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
