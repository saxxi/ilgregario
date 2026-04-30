from urllib.parse import quote_plus

from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

import auth as auth_module

templates = Jinja2Templates(directory="templates")


def _guard(request: Request):
    session = auth_module.get_session(request)
    if not session or not session.get("is_admin"):
        return None, RedirectResponse("/login", status_code=302)
    return session, None


def _redir(path: str, msg: str = "") -> RedirectResponse:
    url = f"{path}?msg={quote_plus(msg)}" if msg else path
    return RedirectResponse(url, status_code=303)
