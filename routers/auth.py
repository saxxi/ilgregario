from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import auth as auth_module
from database import get_db
from templates_env import templates

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if auth_module.get_session(request):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    db = get_db()
    result = db.table("users").select("*").eq("username", username).execute()
    if result.data and auth_module.verify_password(password, result.data[0]["password_hash"]):
        user = result.data[0]
        role = user.get("role") or ("admin" if user.get("is_admin") else "user")
        token = auth_module.create_session_token(user["id"], role=role, username=user["username"])
        dest = "/admin" if role in ("admin", "super_admin") else "/dashboard"
        response = RedirectResponse(dest, status_code=302)
        response.set_cookie(auth_module.SESSION_COOKIE, token, max_age=auth_module.MAX_AGE, httponly=True)
        return response

    return templates.TemplateResponse(request, "login.html", {"error": "Credenziali non valide"}, status_code=401)


@router.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(auth_module.SESSION_COOKIE)
    return response
