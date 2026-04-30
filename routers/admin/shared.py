from urllib.parse import quote_plus

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse

import auth as auth_module
from templates_env import templates


def _guard(request: Request):
    session = auth_module.get_session(request)
    if not session or not session.get("is_admin"):
        return None, RedirectResponse("/login", status_code=302)
    return session, None


async def _guard_post(request: Request):
    session, err = _guard(request)
    if err:
        return session, err
    form = await request.form()
    csrf = str(form.get("csrf_token", ""))
    if not auth_module.verify_csrf_token(csrf, session["user_id"]):
        return None, HTMLResponse("CSRF token non valido", status_code=403)
    return session, None


def _redir(path: str, msg: str = "") -> RedirectResponse:
    url = f"{path}?msg={quote_plus(msg)}" if msg else path
    return RedirectResponse(url, status_code=303)
