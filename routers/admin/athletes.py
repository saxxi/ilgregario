import asyncio
import logging
from urllib.parse import urlparse, parse_qs

from fastapi import APIRouter, BackgroundTasks, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse

from database import get_db
from importers.pcs import PCSImporter
from utils import slugify
from scripts.fetch_athlete_photos import run_missing as _run_missing_photos
from .shared import _guard, _guard_post, _redir, templates

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/admin/athletes/fc-fetch")
async def athletes_fc_fetch(url: str = ""):
    if not url:
        return JSONResponse({"error": "URL mancante"}, status_code=400)
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""

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


@router.post("/admin/athletes/fetch-photos")
async def athletes_fetch_photos(request: Request, background_tasks: BackgroundTasks):
    session, err = await _guard_post(request)
    if err:
        return err
    background_tasks.add_task(_run_missing_photos)
    return _redir("/admin/athletes", "Download foto avviato in background — controlla i log del server.")


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
    session, err = await _guard_post(request)
    if err:
        return err
    db = get_db()
    try:
        name = full_name.strip()
        slug_val = pcs_slug.strip() or slugify(name)
        db.table("athletes").insert({
            "full_name": name,
            "pcs_slug": pcs_slug.strip() or None,
            "slug": slug_val,
            "nationality": nationality.strip() or None,
            "team": team.strip() or None,
            "firstcycling_id": int(firstcycling_id) if firstcycling_id.strip() else None,
            "status": status,
        }).execute()
        return _redir("/admin/athletes", "Atleta aggiunto")
    except Exception:
        logger.exception("athletes_create failed")
        return _redir("/admin/athletes", "Errore interno")


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
    session, err = await _guard_post(request)
    if err:
        return err
    name = full_name.strip()
    slug_val = pcs_slug.strip() or slugify(name)
    get_db().table("athletes").update({
        "full_name": name,
        "pcs_slug": pcs_slug.strip() or None,
        "slug": slug_val,
        "nationality": nationality.strip() or None,
        "team": team.strip() or None,
        "status": status,
    }).eq("id", athlete_id).execute()
    return _redir("/admin/athletes", "Atleta aggiornato")


@router.post("/admin/athletes/{athlete_id}/delete")
async def athletes_delete(request: Request, athlete_id: str):
    session, err = await _guard_post(request)
    if err:
        return err
    get_db().table("athletes").delete().eq("id", athlete_id).execute()
    return _redir("/admin/athletes", "Atleta eliminato")
