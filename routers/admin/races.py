import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from database import get_db
from scoring import score_result
from .shared import _guard, _guard_post, _redir, templates

router = APIRouter()
logger = logging.getLogger(__name__)


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
    session, err = await _guard_post(request)
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
    except Exception:
        logger.exception("races_create failed")
        return _redir("/admin/races", "Errore interno")


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
    session, err = await _guard_post(request)
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
    except Exception:
        logger.exception("races_edit failed")
        return _redir("/admin/races", "Errore interno")


@router.post("/admin/races/{race_id}/delete")
async def races_delete(request: Request, race_id: str):
    session, err = await _guard_post(request)
    if err:
        return err
    get_db().table("races").delete().eq("id", race_id).execute()
    return _redir("/admin/races", "Gara eliminata")


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
    session, err = await _guard_post(request)
    if err:
        return err
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
    except Exception:
        logger.exception("race_results_add failed")
        return _redir(f"/admin/races/{race_id}/results", "Errore interno")


@router.post("/admin/races/{race_id}/results/{result_id}/delete")
async def race_results_delete(request: Request, race_id: str, result_id: str):
    session, err = await _guard_post(request)
    if err:
        return err
    get_db().table("race_results").delete().eq("id", result_id).execute()
    return _redir(f"/admin/races/{race_id}/results", "Risultato eliminato")
