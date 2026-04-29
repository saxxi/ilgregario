from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import auth as auth_module
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if auth_module.get_session(request):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    # Check admin first
    if auth_module.check_admin_credentials(username, password):
        token = auth_module.create_session_token("admin", is_admin=True, username=username)
        response = RedirectResponse("/admin", status_code=302)
        response.set_cookie(auth_module.SESSION_COOKIE, token, max_age=auth_module.MAX_AGE, httponly=True)
        return response

    # Check DB users
    db = get_db()
    result = db.table("users").select("*").eq("username", username).execute()
    if result.data and auth_module.verify_password(password, result.data[0]["password_hash"]):
        user = result.data[0]
        token = auth_module.create_session_token(user["id"], is_admin=user["is_admin"], username=user["username"])
        response = RedirectResponse("/dashboard", status_code=302)
        response.set_cookie(auth_module.SESSION_COOKIE, token, max_age=auth_module.MAX_AGE, httponly=True)
        return response

    return templates.TemplateResponse(request, "login.html", {"error": "Credenziali non valide"}, status_code=401)


@router.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(auth_module.SESSION_COOKIE)
    return response
