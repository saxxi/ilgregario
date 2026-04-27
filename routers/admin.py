from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import auth as auth_module

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/admin", response_class=HTMLResponse)
async def admin_index(request: Request):
    session = auth_module.get_session(request)
    if not session or not session.get("is_admin"):
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse(request, "admin/index.html", {"session": session})
