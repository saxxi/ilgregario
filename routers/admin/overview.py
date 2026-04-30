import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from .shared import _guard, templates

router = APIRouter()


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
